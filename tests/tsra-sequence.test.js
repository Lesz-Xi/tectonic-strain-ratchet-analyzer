'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const sequence = require('../assets/tsra-sequence.js');
const summaryPath = path.join(__dirname, '..', 'data', 'sequence-v0.3', 'summary.json');
const reviewedSummary = JSON.parse(fs.readFileSync(summaryPath, 'utf8'));

class FakeClassList {
    constructor() {
        this.values = new Set();
    }

    add(...names) {
        names.forEach(name => this.values.add(name));
    }

    remove(...names) {
        names.forEach(name => this.values.delete(name));
    }

    contains(name) {
        return this.values.has(name);
    }
}

class FakeElement {
    constructor(id = '') {
        this.id = id;
        this.children = [];
        this.attributes = new Map();
        this.classList = new FakeClassList();
        this.dataset = {};
        this.hidden = false;
        this.textContent = '';
        this.value = '';
        this.disabled = false;
        this.listeners = new Map();
    }

    append(...children) {
        this.children.push(...children);
    }

    replaceChildren(...children) {
        this.children = [...children];
    }

    setAttribute(name, value) {
        this.attributes.set(name, String(value));
    }

    addEventListener(name, handler) {
        this.listeners.set(name, handler);
    }
}

class FakeDocument {
    constructor() {
        this.elements = new Map();
    }

    add(id) {
        const element = new FakeElement(id);
        this.elements.set(id, element);
        return element;
    }

    getElementById(id) {
        return this.elements.get(id) || null;
    }

    createElement() {
        return new FakeElement();
    }

    createElementNS() {
        return new FakeElement();
    }
}

function countSvgClass(element, className) {
    const ownClass = element.attributes && element.attributes.get('class');
    const ownCount = ownClass === className ? 1 : 0;
    return ownCount + element.children.reduce((total, child) => (
        child instanceof FakeElement ? total + countSvgClass(child, className) : total
    ), 0);
}

function ledgerDocument() {
    const documentRef = new FakeDocument();
    [
        'official-ledger-status',
        'official-ledger-blocked',
        'official-ledger-content',
        'official-ledger-body',
        'official-ledger-results',
        'official-ledger-page',
        'ledger-date-start',
        'ledger-date-end',
        'ledger-magnitude-filter',
        'ledger-branch-filter',
        'ledger-filter-reset',
        'ledger-page-prev',
        'ledger-page-next'
    ].forEach(id => documentRef.add(id));
    documentRef.getElementById('official-ledger-content').hidden = true;
    documentRef.getElementById('official-ledger-blocked').hidden = true;
    documentRef.getElementById('ledger-branch-filter').value = 'all';
    return documentRef;
}

function sequenceDocument() {
    const documentRef = new FakeDocument();
    [
        'sequence-root',
        'sequence-verdict',
        'sequence-capture-time',
        'sequence-coverage-start',
        'sequence-last-event',
        'sequence-total-events',
        'sequence-m4-events',
        'sequence-m5-events',
        'sequence-m6-events',
        'sequence-activity-note',
        'sequence-partial-note',
        'sequence-claim-boundary',
        'sequence-activity-chart',
        'sequence-load-status',
        'sequence-blocked-state',
        'sequence-data-content',
        'releases-invariant',
        'releases-final-count',
        'releases-association-note',
        'release-branch-list',
        'significant-release-body',
        'method-baseline',
        'method-tolerance',
        'method-null-occupancy',
        'method-null-occupancy-card',
        'method-selected-fit',
        'method-selected-note',
        'method-verdict',
        'method-timestamp-boundary',
        'method-threshold-body',
        'method-original-body',
        'method-limitations'
    ].forEach(id => documentRef.add(id));
    documentRef.getElementById('sequence-blocked-state').hidden = true;
    return documentRef;
}

test('reviewed summary satisfies the browser contract', () => {
    assert.deepEqual(sequence.validateSummary(reviewedSummary), []);
});

test('browser contract rejects daily conservation drift', () => {
    const corrupted = structuredClone(reviewedSummary);
    corrupted.dailyActivity[0].eventCount -= 1;

    const errors = sequence.validateSummary(corrupted);

    assert.ok(errors.includes('dailyActivity[0] magnitude classes do not conserve'));
    assert.ok(errors.includes('daily activity does not conserve to the official event total'));
});

test('browser contract rejects spatial and final-bulletin drift', () => {
    const corrupted = structuredClone(reviewedSummary);
    corrupted.spatialBranches[0].eventCount -= 1;
    corrupted.significantEvents[0].finalBulletinUrl = 'https://example.com/not-phivolcs';

    const errors = sequence.validateSummary(corrupted);

    assert.ok(errors.includes('spatial branches do not conserve to the official event total'));
    assert.ok(errors.includes('significantEvents[0].finalBulletinUrl is invalid'));
});

test('browser contract rejects loss of the original method provenance', () => {
    const corrupted = structuredClone(reviewedSummary);
    corrupted.historicalClockAudit.originalInvestigation.events.pop();

    const errors = sequence.validateSummary(corrupted);

    assert.ok(errors.includes('original 11-event investigation is missing'));
});

test('successful load renders evidence metrics and the activity chart', async () => {
    const documentRef = sequenceDocument();
    const fetchImpl = async (url, options) => {
        assert.equal(url, sequence.SUMMARY_URL);
        assert.equal(options.headers.Accept, 'application/json');
        return {
            ok: true,
            json: async () => structuredClone(reviewedSummary)
        };
    };

    const result = await sequence.loadSequence(documentRef, fetchImpl);

    assert.equal(result.ok, true);
    assert.equal(documentRef.getElementById('sequence-root').dataset.state, 'ready');
    assert.equal(documentRef.getElementById('sequence-total-events').textContent, '1202');
    assert.equal(documentRef.getElementById('sequence-m4-events').textContent, '42');
    assert.match(documentRef.getElementById('sequence-verdict').textContent, /punctuated aftershock decay/i);
    assert.match(documentRef.getElementById('sequence-partial-note').textContent, /Jun 9–29 has no reviewed catalog coverage/i);
    assert.equal(reviewedSummary.dailyActivity[0].coverage, 'anchor_only_mainshock');
    assert.equal(reviewedSummary.dailyActivity[1].coverage, 'not_captured');
    const chart = documentRef.getElementById('sequence-activity-chart');
    assert.ok(chart.children.length > 30);
    assert.equal(countSvgClass(chart, 'sequence-gap-band'), 1);
    assert.equal(countSvgClass(chart, 'sequence-gap-label'), 1);
    assert.equal(countSvgClass(chart, 'sequence-mainshock-guide'), 1);
    assert.equal(countSvgClass(chart, 'sequence-mainshock-label'), 1);
    assert.equal(countSvgClass(chart, 'sequence-day-gap'), 0);
    assert.equal(documentRef.getElementById('release-branch-list').children.length, 3);
    assert.equal(documentRef.getElementById('significant-release-body').children.length, 17);
    assert.match(documentRef.getElementById('releases-invariant').textContent, /5 of 9 M5\+ releases/i);
    assert.equal(documentRef.getElementById('method-threshold-body').children.length, 5);
    assert.equal(documentRef.getElementById('method-original-body').children.length, 11);
    assert.match(documentRef.getElementById('method-selected-fit').textContent, /8\/9 · 88\.9%/);
    assert.match(documentRef.getElementById('method-verdict').textContent, /no validated single-period clock/i);
    assert.equal(documentRef.getElementById('sequence-blocked-state').hidden, true);
});

test('official ledger parser preserves all verified rows and newest-first order', () => {
    const csvText = fs.readFileSync(path.join(__dirname, '..', 'data', 'sequence-v0.3', 'events.csv'), 'utf8');

    const events = sequence.parseOfficialLedger(csvText);

    assert.equal(events.length, 1202);
    assert.equal(events[0].id, 'PHV-1201');
    assert.equal(events.at(-1).id, 'PHV-MAIN-20260608');
    assert.equal(sequence.filterLedgerEvents(events, {
        startDate: '', endDate: '', minimumMagnitude: 5, branch: 'all'
    }).length, 9);
    assert.equal(sequence.filterLedgerEvents(events, {
        startDate: '', endDate: '', minimumMagnitude: null, branch: 'southOffshore'
    }).length, 183);
    assert.equal(sequence.filterLedgerEvents(events, {
        startDate: '2026-07-14', endDate: '2026-07-14', minimumMagnitude: 4.5, branch: 'all'
    }).length, 3);
});

test('lazy ledger load renders one bounded page without touching the sequence path', async () => {
    const documentRef = ledgerDocument();
    const csvText = fs.readFileSync(path.join(__dirname, '..', 'data', 'sequence-v0.3', 'events.csv'), 'utf8');
    const fetchImpl = async (url, options) => {
        assert.equal(url, sequence.EVENTS_URL);
        assert.equal(options.headers.Accept, 'text/csv');
        return { ok: true, text: async () => csvText };
    };

    const result = await sequence.loadLedger(documentRef, fetchImpl);

    assert.equal(result.ok, true);
    assert.equal(result.events.length, 1202);
    assert.equal(documentRef.getElementById('official-ledger-body').children.length, 100);
    assert.match(documentRef.getElementById('official-ledger-results').textContent, /1202 matching rows/);
    assert.equal(documentRef.getElementById('official-ledger-page').textContent, 'Page 1 of 13');
    assert.equal(documentRef.getElementById('official-ledger-content').hidden, false);
});

test('failed load blocks the surface without substituting zero values', async () => {
    const documentRef = sequenceDocument();
    const fetchImpl = async () => ({ ok: false, status: 503 });

    const result = await sequence.loadSequence(documentRef, fetchImpl);

    assert.equal(result.ok, false);
    assert.equal(documentRef.getElementById('sequence-root').dataset.state, 'blocked');
    assert.equal(documentRef.getElementById('sequence-blocked-state').hidden, false);
    assert.equal(documentRef.getElementById('sequence-data-content').hidden, true);
    assert.equal(documentRef.getElementById('sequence-total-events').textContent, '');
    assert.match(documentRef.getElementById('sequence-blocked-state').textContent, /no zero values or live state/i);
});
