(function sequenceModule(globalScope) {
    'use strict';

    const SUMMARY_URL = '/data/sequence-v0.3/summary.json';
    const EVENTS_URL = '/data/sequence-v0.3/events.csv';
    const EXPECTED_DATASET_ID = 'tsra-sarangani-cotabato-sequence-v0.3';
    const EXPECTED_EVENT_ROWS = 1202;
    const LEDGER_PAGE_SIZE = 100;
    const SVG_NS = 'http://www.w3.org/2000/svg';
    const ledgerState = {
        status: 'idle',
        events: [],
        page: 1,
        filtersBound: false,
        promise: null
    };
    const STACKS = [
        { key: 'belowM2', label: 'Below M2', className: 'sequence-bar--below-m2' },
        { key: 'm2To2_9', label: 'M2–2.9', className: 'sequence-bar--m2' },
        { key: 'm3To3_9', label: 'M3–3.9', className: 'sequence-bar--m3' },
        { key: 'm4To4_9', label: 'M4–4.9', className: 'sequence-bar--m4' },
        { key: 'm5AndAbove', label: 'M5+', className: 'sequence-bar--m5' }
    ];

    function isObject(value) {
        return value !== null && typeof value === 'object' && !Array.isArray(value);
    }

    function isFiniteNumber(value) {
        return typeof value === 'number' && Number.isFinite(value);
    }

    function validateSummary(summary) {
        const errors = [];
        if (!isObject(summary)) return ['summary must be an object'];
        if (summary.schemaVersion !== 1) errors.push('unsupported summary schema');
        if (summary.datasetId !== EXPECTED_DATASET_ID) errors.push('unexpected dataset identity');

        const capture = summary.capture;
        if (!isObject(capture)) {
            errors.push('capture metadata is missing');
        } else {
            if (capture.isLive !== false) errors.push('snapshot must explicitly be static');
            for (const key of ['capturedAtPht', 'coverageStartPht', 'lastIncludedEventPht']) {
                if (typeof capture[key] !== 'string' || !capture[key]) errors.push(`capture.${key} is missing`);
            }
        }

        const interpretation = summary.interpretation;
        if (!isObject(interpretation) || typeof interpretation.standing !== 'string') {
            errors.push('standing interpretation is missing');
        }
        if (!isObject(interpretation) || !String(interpretation.classification || '').toLowerCase().includes('inference')) {
            errors.push('standing interpretation must be classified as inference');
        }

        const counts = summary.counts;
        if (!isObject(counts)) {
            errors.push('counts are missing');
        } else {
            for (const key of ['officialPhivolcsRowsDeduplicated', 'm4AndAbove', 'm5AndAbove', 'm6AndAbove']) {
                if (!Number.isInteger(counts[key]) || counts[key] < 0) errors.push(`counts.${key} is invalid`);
            }
        }

        if (!Array.isArray(summary.dailyActivity) || summary.dailyActivity.length === 0) {
            errors.push('daily activity is missing');
        } else {
            let dailyTotal = 0;
            summary.dailyActivity.forEach((day, index) => {
                if (!isObject(day)) {
                    errors.push(`dailyActivity[${index}] is invalid`);
                    return;
                }
                if (typeof day.datePht !== 'string' || !day.datePht) errors.push(`dailyActivity[${index}].datePht is invalid`);
                if (!Number.isInteger(day.eventCount) || day.eventCount < 0) errors.push(`dailyActivity[${index}].eventCount is invalid`);
                const stackTotal = STACKS.reduce((total, stack) => {
                    const value = day[stack.key];
                    if (!Number.isInteger(value) || value < 0) {
                        errors.push(`dailyActivity[${index}].${stack.key} is invalid`);
                        return total;
                    }
                    return total + value;
                }, 0);
                if (Number.isInteger(day.eventCount) && stackTotal !== day.eventCount) {
                    errors.push(`dailyActivity[${index}] magnitude classes do not conserve`);
                }
                if (Number.isInteger(day.eventCount)) dailyTotal += day.eventCount;
            });
            if (isObject(counts) && Number.isInteger(counts.officialPhivolcsRowsDeduplicated)
                && dailyTotal !== counts.officialPhivolcsRowsDeduplicated) {
                errors.push('daily activity does not conserve to the official event total');
            }
        }

        if (!Array.isArray(summary.spatialBranches) || summary.spatialBranches.length !== 3) {
            errors.push('three spatial branches are required');
        } else {
            const branchTotal = summary.spatialBranches.reduce((total, branch, index) => {
                if (!isObject(branch)) {
                    errors.push(`spatialBranches[${index}] is invalid`);
                    return total;
                }
                for (const key of ['id', 'label', 'rule']) {
                    if (typeof branch[key] !== 'string' || !branch[key]) errors.push(`spatialBranches[${index}].${key} is invalid`);
                }
                for (const key of ['eventCount', 'm4AndAbove', 'm5AndAbove']) {
                    if (!Number.isInteger(branch[key]) || branch[key] < 0) errors.push(`spatialBranches[${index}].${key} is invalid`);
                }
                if (!isFiniteNumber(branch.fraction) || branch.fraction < 0 || branch.fraction > 1) {
                    errors.push(`spatialBranches[${index}].fraction is invalid`);
                }
                if (!isFiniteNumber(branch.medianDepthKm) || branch.medianDepthKm < 0) {
                    errors.push(`spatialBranches[${index}].medianDepthKm is invalid`);
                }
                return total + (Number.isInteger(branch.eventCount) ? branch.eventCount : 0);
            }, 0);
            if (isObject(counts) && Number.isInteger(counts.officialPhivolcsRowsDeduplicated)
                && branchTotal !== counts.officialPhivolcsRowsDeduplicated) {
                errors.push('spatial branches do not conserve to the official event total');
            }
        }

        if (!Array.isArray(summary.significantEvents) || summary.significantEvents.length !== 17) {
            errors.push('17 significant final-bulletin events are required');
        } else {
            summary.significantEvents.forEach((event, index) => {
                if (!isObject(event)) {
                    errors.push(`significantEvents[${index}] is invalid`);
                    return;
                }
                if (typeof event.timePht !== 'string' || !event.timePht) errors.push(`significantEvents[${index}].timePht is invalid`);
                if (!isFiniteNumber(event.magnitude) || event.magnitude < 4.5) errors.push(`significantEvents[${index}].magnitude is invalid`);
                if (!isFiniteNumber(event.depthKm) || event.depthKm < 0) errors.push(`significantEvents[${index}].depthKm is invalid`);
                if (typeof event.location !== 'string' || !event.location) errors.push(`significantEvents[${index}].location is invalid`);
                if (typeof event.finalBulletinUrl !== 'string' || !event.finalBulletinUrl.startsWith('https://earthquake.phivolcs.dost.gov.ph/')) {
                    errors.push(`significantEvents[${index}].finalBulletinUrl is invalid`);
                }
                if (typeof event.officialSequenceStatement !== 'string' || !event.officialSequenceStatement.includes('aftershock of June 2026')) {
                    errors.push(`significantEvents[${index}] is missing its final association statement`);
                }
            });
        }

        const audit = summary.historicalClockAudit;
        if (!isObject(audit)) {
            errors.push('historical clock audit is missing');
        } else {
            if (!isFiniteNumber(audit.baselineMinutes) || !isFiniteNumber(audit.nullBaselineMinutes)) {
                errors.push('historical clock baselines are invalid');
            }
            if (!isFiniteNumber(audit.toleranceMinutes) || audit.toleranceMinutes <= 0) {
                errors.push('historical clock tolerance is invalid');
            }
            if (!isFiniteNumber(audit.uniformModuloNullProbability)) {
                errors.push('historical null occupancy is invalid');
            }
            if (typeof audit.status !== 'string' || !audit.status.includes('no validated single-period clock')) {
                errors.push('historical clock non-validation boundary is missing');
            }
            if (!Array.isArray(audit.thresholds) || audit.thresholds.length !== 5) {
                errors.push('historical threshold audit is incomplete');
            }
            const original = audit.originalInvestigation;
            if (!isObject(original) || !Array.isArray(original.events) || original.events.length !== 11) {
                errors.push('original 11-event investigation is missing');
            } else {
                if (original.standardIntervalCount !== 9 || original.insideToleranceCount !== 8) {
                    errors.push('original selected calibration counts changed');
                }
                if (typeof original.status !== 'string' || !original.status.includes('historical')) {
                    errors.push('original investigation provenance boundary is missing');
                }
            }
        }

        if (!Array.isArray(summary.sourceBoundaries) || summary.sourceBoundaries.length === 0) {
            errors.push('source boundaries are missing');
        }
        return [...new Set(errors)];
    }

    function formatPht(value, options) {
        const normalized = typeof value === 'string' && !/(?:Z|[+-]\d{2}:\d{2})$/i.test(value)
            ? `${value}+08:00`
            : value;
        const date = new Date(normalized);
        if (Number.isNaN(date.getTime())) return 'Unavailable';
        return new Intl.DateTimeFormat('en-PH', {
            timeZone: 'Asia/Manila',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            ...options
        }).format(date);
    }

    function formatDay(value) {
        const date = new Date(`${value}T00:00:00+08:00`);
        if (Number.isNaN(date.getTime())) return value;
        return new Intl.DateTimeFormat('en-PH', {
            timeZone: 'Asia/Manila',
            month: 'short',
            day: 'numeric'
        }).format(date);
    }

    function setText(documentRef, id, value) {
        const element = documentRef.getElementById(id);
        if (element) element.textContent = value;
    }

    function createSvgElement(documentRef, name, attributes) {
        const element = documentRef.createElementNS(SVG_NS, name);
        Object.entries(attributes || {}).forEach(([key, value]) => element.setAttribute(key, String(value)));
        return element;
    }

    function appendSvgText(documentRef, svg, text, attributes) {
        const element = createSvgElement(documentRef, 'text', attributes);
        element.textContent = text;
        svg.append(element);
        return element;
    }

    function describeDay(day) {
        const rows = [];
        STACKS.forEach(stack => {
            const value = day[stack.key];
            if (value) rows.push({ label: stack.label, value, className: stack.className });
        });
        return rows;
    }

    function coverageNote(day) {
        if (day.coverage === 'anchor_only_mainshock') return 'Sequence anchor only · not a complete public day';
        if (day.coverage === 'not_captured') return 'No reviewed catalog coverage';
        if (day.coverage === 'partial_from_08:00') return 'Partial day · capture begins 08:00 PHT';
        if (day.coverage === 'partial_at_capture') return 'Partial day · capture cut at the snapshot time';
        return '';
    }

    function bindDayTooltip(documentRef, group, day) {
        const tooltip = documentRef.getElementById('sequence-chart-tooltip');
        if (!tooltip || typeof group.addEventListener !== 'function') return;

        const show = () => {
            tooltip.replaceChildren();

            const head = createHtmlElement(documentRef, 'div', 'sequence-tip-head');
            head.append(
                createHtmlElement(documentRef, 'span', 'sequence-tip-date', formatDay(day.datePht)),
                createHtmlElement(documentRef, 'span', 'sequence-tip-total', `${day.eventCount} rows`)
            );
            tooltip.append(head);

            const note = coverageNote(day);
            if (note) tooltip.append(createHtmlElement(documentRef, 'div', 'sequence-tip-coverage', note));

            const list = createHtmlElement(documentRef, 'dl', 'sequence-tip-list');
            describeDay(day).forEach(row => {
                const term = createHtmlElement(documentRef, 'dt', 'sequence-tip-term');
                term.append(createHtmlElement(documentRef, 'i', `sequence-tip-swatch ${row.className}`));
                term.append(createHtmlElement(documentRef, 'span', null, row.label));
                list.append(term, createHtmlElement(documentRef, 'dd', 'sequence-tip-value', String(row.value)));
            });
            tooltip.append(list);

            tooltip.append(createHtmlElement(documentRef, 'div', 'sequence-tip-max',
                `Maximum magnitude M${day.maxMagnitude} · official PHIVOLCS rows, not felt reports`));

            tooltip.classList.add('is-visible');
            tooltip.hidden = false;
        };

        const hide = () => {
            tooltip.classList.remove('is-visible');
            tooltip.hidden = true;
        };

        const track = event => {
            const wrap = documentRef.getElementById('sequence-chart-wrap');
            if (!wrap || typeof wrap.getBoundingClientRect !== 'function') return;
            const bounds = wrap.getBoundingClientRect();
            const x = event.clientX - bounds.left + wrap.scrollLeft;
            const y = event.clientY - bounds.top;

            // Flip before the plate would cross the visible right edge of the scroller.
            const visibleRight = wrap.scrollLeft + bounds.width;
            const flip = x + tooltip.offsetWidth + 24 > visibleRight;
            tooltip.classList.toggle('is-flipped', flip);

            const margin = 12;
            const clampedY = Math.min(Math.max(y, tooltip.offsetHeight / 2 + margin),
                bounds.height - tooltip.offsetHeight / 2 - margin);

            tooltip.style.setProperty('--tip-x', `${x}px`);
            tooltip.style.setProperty('--tip-y', `${Number.isFinite(clampedY) ? clampedY : y}px`);
        };

        // Keyboard focus has no pointer position, so anchor the plate to the bar itself.
        const anchorToGroup = () => {
            const wrap = documentRef.getElementById('sequence-chart-wrap');
            if (!wrap || typeof wrap.getBoundingClientRect !== 'function'
                || typeof group.getBoundingClientRect !== 'function') return;
            const bounds = wrap.getBoundingClientRect();
            const box = group.getBoundingClientRect();
            track({
                clientX: box.left + box.width / 2,
                clientY: Math.max(box.top, bounds.top) + Math.min(box.height, bounds.height) / 2
            });
            if (typeof group.scrollIntoView === 'function') {
                group.scrollIntoView({ block: 'nearest', inline: 'nearest' });
            }
        };

        group.addEventListener('pointerenter', show);
        group.addEventListener('pointermove', track);
        group.addEventListener('pointerleave', hide);
        group.addEventListener('focus', () => { show(); anchorToGroup(); });
        group.addEventListener('blur', hide);
    }

    function renderActivityChart(documentRef, days) {
        const svg = documentRef.getElementById('sequence-activity-chart');
        if (!svg) return;
        svg.replaceChildren();

        const width = 1000;
        const height = 340;
        const margin = { top: 34, right: 20, bottom: 54, left: 58 };
        const plotWidth = width - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;
        const maximum = Math.max(...days.map(day => day.eventCount));
        const axisMaximum = Math.max(20, Math.ceil(maximum / 20) * 20);
        const slot = plotWidth / days.length;
        const barWidth = Math.max(12, slot * 0.58);

        // aria-label, not a chart-level <title>: an SVG <title> fires the browser's
        // native hover tooltip for every descendant that doesn't have a nearer one of
        // its own, which collided with the per-bar reading plate below.
        const description = createSvgElement(documentRef, 'desc', { id: 'sequence-chart-description' });
        description.textContent = 'Sequence timeline from the directly reviewed June 8 mainshock anchor through the partial July 22 capture. June 9–29 is marked as an explicit no-data gap; continuous catalog coverage begins June 30 at 08:00 PHT.';
        svg.append(description);
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.setAttribute('role', 'img');
        svg.setAttribute('aria-label', 'Daily PHIVOLCS activity by magnitude class');
        svg.setAttribute('aria-describedby', 'sequence-chart-description');

        for (let tick = 0; tick <= axisMaximum; tick += 20) {
            const y = margin.top + plotHeight - (tick / axisMaximum) * plotHeight;
            svg.append(createSvgElement(documentRef, 'line', {
                x1: margin.left,
                x2: width - margin.right,
                y1: y,
                y2: y,
                class: 'sequence-chart-gridline'
            }));
            appendSvgText(documentRef, svg, String(tick), {
                x: margin.left - 12,
                y: y + 4,
                'text-anchor': 'end',
                class: 'sequence-chart-axis-label'
            });
        }

        days.forEach((day, index) => {
            const x = margin.left + index * slot + (slot - barWidth) / 2;
            let accumulated = 0;
            const coverage = coverageNote(day);
            const magnitudeReading = day.maxMagnitude === null
                ? 'no captured events'
                : `maximum M${day.maxMagnitude}`;
            const group = createSvgElement(documentRef, 'g', {
                class: 'sequence-day-group',
                tabindex: '0',
                role: 'img',
                'aria-label': `${formatDay(day.datePht)}: ${day.eventCount} official rows, ${magnitudeReading}`
                    + `${coverage ? `, ${coverage}` : ''}. `
                    + describeDay(day).map(row => `${row.label} ${row.value}`).join(', ')
            });

            group.append(createSvgElement(documentRef, 'rect', {
                x: margin.left + index * slot,
                y: margin.top,
                width: slot,
                height: plotHeight,
                class: 'sequence-day-hit'
            }));

            if (day.coverage === 'not_captured') {
                group.append(createSvgElement(documentRef, 'rect', {
                    x: margin.left + index * slot + 1,
                    y: margin.top,
                    width: Math.max(slot - 2, 1),
                    height: plotHeight,
                    class: 'sequence-day-gap'
                }));
            }

            STACKS.forEach(stack => {
                const value = day[stack.key];
                if (!value) return;
                const segmentHeight = (value / axisMaximum) * plotHeight;
                const y = margin.top + plotHeight - ((accumulated + value) / axisMaximum) * plotHeight;
                group.append(createSvgElement(documentRef, 'rect', {
                    x,
                    y,
                    width: barWidth,
                    height: Math.max(segmentHeight, 1),
                    rx: 1.5,
                    class: `sequence-bar ${stack.className}`
                }));
                accumulated += value;
            });

            if (day.coverage.startsWith('partial') || day.coverage === 'anchor_only_mainshock') {
                const totalHeight = (day.eventCount / axisMaximum) * plotHeight;
                group.append(createSvgElement(documentRef, 'rect', {
                    x: x - 2,
                    y: margin.top + plotHeight - totalHeight - 2,
                    width: barWidth + 4,
                    height: totalHeight + 4,
                    rx: 2,
                    class: day.coverage === 'anchor_only_mainshock' ? 'sequence-bar-anchor' : 'sequence-bar-partial'
                }));
            }
            bindDayTooltip(documentRef, group, day);
            svg.append(group);

            if (index % 2 === 0 || index === days.length - 1) {
                appendSvgText(documentRef, svg, formatDay(day.datePht), {
                    x: x + barWidth / 2,
                    y: height - 25,
                    'text-anchor': 'middle',
                    class: 'sequence-chart-axis-label sequence-chart-date-label'
                });
            }
        });

        appendSvgText(documentRef, svg, 'Official rows / day', {
            x: 16,
            y: margin.top + plotHeight / 2,
            transform: `rotate(-90 16 ${margin.top + plotHeight / 2})`,
            'text-anchor': 'middle',
            class: 'sequence-chart-axis-title'
        });
        svg.setAttribute('aria-busy', 'false');
    }

    function average(days) {
        if (!days.length) return 0;
        return days.reduce((total, day) => total + day.eventCount, 0) / days.length;
    }

    function createHtmlElement(documentRef, tag, className, text) {
        const element = documentRef.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = text;
        return element;
    }

    function appendReleaseMetric(documentRef, container, label, value) {
        const metric = createHtmlElement(documentRef, 'div', 'release-branch-metric');
        metric.append(
            createHtmlElement(documentRef, 'span', 'release-branch-metric-label', label),
            createHtmlElement(documentRef, 'strong', 'release-branch-metric-value', value)
        );
        container.append(metric);
    }

    function renderReleases(documentRef, summary) {
        const branches = summary.spatialBranches;
        const significantEvents = summary.significantEvents;
        const south = branches.find(branch => branch.id === 'southOffshore');
        const north = branches.find(branch => branch.id === 'glanMaasimNorth');
        const totalM5 = branches.reduce((total, branch) => total + branch.m5AndAbove, 0);

        if (south && north) {
            setText(documentRef, 'releases-invariant',
                `${(north.fraction * 100).toFixed(1)}% of catalog rows occur in the Glan–Maasim north branch, `
                + `while ${south.m5AndAbove} of ${totalM5} M5+ releases occur south offshore.`
            );
        }
        setText(documentRef, 'releases-final-count', String(significantEvents.length));
        setText(documentRef, 'releases-association-note',
            `${significantEvents.length} directly inspected final PHIVOLCS bulletins explicitly associate these releases with the June sequence. `
            + `Smaller AOI rows are not automatically assigned.`
        );

        const branchContainer = documentRef.getElementById('release-branch-list');
        if (branchContainer) {
            branchContainer.replaceChildren();
            branches.forEach((branch, index) => {
                const article = createHtmlElement(documentRef, 'article', 'release-branch');
                article.dataset.branch = branch.id;
                const header = createHtmlElement(documentRef, 'header', 'release-branch-head');
                const headingGroup = createHtmlElement(documentRef, 'div');
                headingGroup.append(
                    createHtmlElement(documentRef, 'div', 'release-branch-index', `0${index + 1}`),
                    createHtmlElement(documentRef, 'h3', 'release-branch-title', branch.label),
                    createHtmlElement(documentRef, 'p', 'release-branch-rule', branch.rule)
                );
                header.append(
                    headingGroup,
                    createHtmlElement(documentRef, 'div', 'release-branch-share', `${(branch.fraction * 100).toFixed(1)}%`)
                );

                const track = createHtmlElement(documentRef, 'div', 'release-branch-track');
                const fill = createHtmlElement(documentRef, 'span', 'release-branch-fill');
                fill.setAttribute('style', `width:${(branch.fraction * 100).toFixed(3)}%`);
                track.append(fill);

                const metrics = createHtmlElement(documentRef, 'div', 'release-branch-metrics');
                appendReleaseMetric(documentRef, metrics, 'Official rows', String(branch.eventCount));
                appendReleaseMetric(documentRef, metrics, 'M4+', String(branch.m4AndAbove));
                appendReleaseMetric(documentRef, metrics, 'M5+', String(branch.m5AndAbove));
                appendReleaseMetric(documentRef, metrics, 'Median depth', `${branch.medianDepthKm.toFixed(0)} km`);
                article.append(header, track, metrics);
                branchContainer.append(article);
            });
        }

        const releaseBody = documentRef.getElementById('significant-release-body');
        if (releaseBody) {
            releaseBody.replaceChildren();
            significantEvents.forEach(event => {
                const row = createHtmlElement(documentRef, 'tr');
                const timeCell = createHtmlElement(documentRef, 'td', 'mono', formatPht(event.timePht));
                const magnitudeCell = createHtmlElement(documentRef, 'td');
                magnitudeCell.append(createHtmlElement(documentRef, 'strong', 'release-magnitude', `${event.magnitudeType}${event.magnitude.toFixed(1)}`));
                const depthCell = createHtmlElement(documentRef, 'td', 'mono', `${event.depthKm.toFixed(0)} km`);
                const locationCell = createHtmlElement(documentRef, 'td', 'release-location', event.location);
                const intensityCell = createHtmlElement(documentRef, 'td', 'mono', event.maxReportedIntensity || 'Not listed');
                const sourceCell = createHtmlElement(documentRef, 'td');
                const sourceLink = createHtmlElement(documentRef, 'a', 'release-source-link', 'Final bulletin');
                sourceLink.setAttribute('href', event.finalBulletinUrl);
                sourceLink.setAttribute('target', '_blank');
                sourceLink.setAttribute('rel', 'noopener noreferrer');
                sourceCell.append(sourceLink);
                row.append(timeCell, magnitudeCell, depthCell, locationCell, intensityCell, sourceCell);
                releaseBody.append(row);
            });
        }
    }

    function formatPercent(value, digits) {
        return `${(value * 100).toFixed(digits === undefined ? 1 : digits)}%`;
    }

    function renderMethod(documentRef, summary) {
        const audit = summary.historicalClockAudit;
        const original = audit.originalInvestigation;
        setText(documentRef, 'method-baseline', `${audit.baselineMinutes.toFixed(3)} min`);
        setText(documentRef, 'method-tolerance', `±${audit.toleranceMinutes.toFixed(0)} min`);
        setText(documentRef, 'method-null-occupancy', formatPercent(audit.uniformModuloNullProbability, 1));
        setText(documentRef, 'method-null-occupancy-card', formatPercent(audit.uniformModuloNullProbability, 1));
        setText(documentRef, 'method-selected-fit', `${original.insideToleranceCount}/${original.standardIntervalCount} · ${formatPercent(original.selectedAlignmentFraction, 1)}`);
        setText(documentRef, 'method-selected-note', `Median absolute offset ${original.medianAbsoluteOffsetMinutes.toFixed(1)} min across the selected standard intervals.`);
        setText(documentRef, 'method-verdict', audit.status);
        setText(documentRef, 'method-timestamp-boundary', original.timestampBoundary);

        const thresholdBody = documentRef.getElementById('method-threshold-body');
        if (thresholdBody) {
            thresholdBody.replaceChildren();
            audit.thresholds.forEach(threshold => {
                const row = createHtmlElement(documentRef, 'tr');
                const thresholdLabel = Number.isInteger(threshold.minimumMagnitude)
                    ? `M${threshold.minimumMagnitude.toFixed(0)}+`
                    : `M${threshold.minimumMagnitude.toFixed(1)}+`;
                appendLedgerCell(documentRef, row, thresholdLabel, 'mono');
                appendLedgerCell(documentRef, row, String(threshold.eventCount), 'mono');
                appendLedgerCell(documentRef, row, `${threshold.medianIntervalMinutes.toFixed(1)} min`, 'mono');
                appendLedgerCell(
                    documentRef,
                    row,
                    `${threshold.alignmentCount}/${threshold.intervalCount} · ${formatPercent(threshold.alignmentFraction, 1)}`,
                    'mono'
                );
                appendLedgerCell(documentRef, row, formatPercent(threshold.uniformModuloNullProbability, 1), 'mono');
                appendLedgerCell(documentRef, row, threshold.descriptiveOneSidedBinomialPValue.toFixed(3), 'mono');
                const reading = threshold.descriptiveOneSidedBinomialPValue < 0.05
                    ? 'Descriptive excess; not a clock test under clustered, selected data'
                    : 'Not unusual under the permissive modulo null';
                appendLedgerCell(documentRef, row, reading, 'method-reading');
                thresholdBody.append(row);
            });
        }

        const originalBody = documentRef.getElementById('method-original-body');
        if (originalBody) {
            originalBody.replaceChildren();
            original.events.forEach(event => {
                const row = createHtmlElement(documentRef, 'tr');
                appendLedgerCell(documentRef, row, event.label, 'mono');
                appendLedgerCell(documentRef, row, event.displayTimePht, 'mono');
                appendLedgerCell(documentRef, row, event.intervalMinutes === null ? '—' : `${event.intervalMinutes.toFixed(1)} min`, 'mono');
                appendLedgerCell(documentRef, row, event.nearestPhase || '—', 'mono');
                appendLedgerCell(
                    documentRef,
                    row,
                    event.offsetMinutes === null ? '—' : `${event.offsetMinutes >= 0 ? '+' : '−'}${Math.abs(event.offsetMinutes).toFixed(1)} min`,
                    'mono'
                );
                const resultCell = appendLedgerCell(documentRef, row, event.result, 'method-result');
                resultCell.dataset.result = event.result;
                originalBody.append(row);
            });
        }

        const limitations = documentRef.getElementById('method-limitations');
        if (limitations) {
            limitations.replaceChildren();
            audit.limitations.forEach(item => limitations.append(createHtmlElement(documentRef, 'li', '', item)));
        }
    }

    function parseCsv(text) {
        if (typeof text !== 'string' || !text.trim()) throw new Error('official ledger CSV is empty');
        const rows = [];
        let row = [];
        let field = '';
        let quoted = false;

        for (let index = 0; index < text.length; index += 1) {
            const character = text[index];
            if (quoted) {
                if (character === '"' && text[index + 1] === '"') {
                    field += '"';
                    index += 1;
                } else if (character === '"') {
                    quoted = false;
                } else {
                    field += character;
                }
                continue;
            }
            if (character === '"') {
                quoted = true;
            } else if (character === ',') {
                row.push(field);
                field = '';
            } else if (character === '\n') {
                row.push(field.endsWith('\r') ? field.slice(0, -1) : field);
                if (row.some(value => value !== '')) rows.push(row);
                row = [];
                field = '';
            } else {
                field += character;
            }
        }
        if (quoted) throw new Error('official ledger CSV contains an unterminated quoted field');
        if (field || row.length) {
            row.push(field.endsWith('\r') ? field.slice(0, -1) : field);
            if (row.some(value => value !== '')) rows.push(row);
        }
        if (rows.length < 2) throw new Error('official ledger CSV has no data rows');
        const headers = rows[0];
        return rows.slice(1).map((values, rowIndex) => {
            if (values.length !== headers.length) {
                throw new Error(`official ledger row ${rowIndex + 1} has ${values.length} fields; expected ${headers.length}`);
            }
            return Object.fromEntries(headers.map((header, index) => [header, values[index]]));
        });
    }

    function ledgerBranch(latitude) {
        if (latitude < 5.2) return 'southOffshore';
        if (latitude < 5.5) return 'balutCentral';
        return 'glanMaasimNorth';
    }

    function normalizeLedgerRows(rows) {
        const required = [
            'event_key', 'time_pht', 'latitude', 'longitude', 'depth_km', 'magnitude',
            'location', 'bulletin_url', 'source_class', 'sequence_association_status'
        ];
        const seen = new Set();
        const events = rows.map((row, index) => {
            const rowNumber = index + 1;
            for (const field of required) {
                if (typeof row[field] !== 'string' || !row[field]) {
                    throw new Error(`official ledger row ${rowNumber} is missing ${field}`);
                }
            }
            if (seen.has(row.event_key)) throw new Error(`duplicate official ledger event key: ${row.event_key}`);
            seen.add(row.event_key);
            const latitude = Number(row.latitude);
            const longitude = Number(row.longitude);
            const depthKm = Number(row.depth_km);
            const magnitude = Number(row.magnitude);
            const timestamp = Date.parse(`${row.time_pht}+08:00`);
            if (![latitude, longitude, depthKm, magnitude, timestamp].every(Number.isFinite)) {
                throw new Error(`official ledger row ${rowNumber} contains an invalid numeric or time field`);
            }
            if (latitude < 4.2 || latitude > 6.2 || longitude < 124.5 || longitude > 126.0) {
                throw new Error(`official ledger event falls outside the declared AOI: ${row.event_key}`);
            }
            if (!row.bulletin_url.startsWith('https://earthquake.phivolcs.dost.gov.ph/')) {
                throw new Error(`official ledger event has an invalid PHIVOLCS URL: ${row.event_key}`);
            }
            if (row.source_class !== 'official_phivolcs_public_bulletin_row') {
                throw new Error(`official ledger event has an invalid source class: ${row.event_key}`);
            }
            if (!row.sequence_association_status.includes('spatial_AOI_inclusion_only')) {
                throw new Error(`official ledger event lost its AOI-only association boundary: ${row.event_key}`);
            }
            return {
                id: row.event_key,
                timePht: row.time_pht,
                timestamp,
                datePht: row.time_pht.slice(0, 10),
                latitude,
                longitude,
                depthKm,
                magnitude,
                location: row.location,
                bulletinUrl: row.bulletin_url,
                branch: ledgerBranch(latitude)
            };
        });
        if (events.length !== EXPECTED_EVENT_ROWS) {
            throw new Error(`official ledger row count is ${events.length}; expected ${EXPECTED_EVENT_ROWS}`);
        }
        for (let index = 1; index < events.length; index += 1) {
            if (events[index].timestamp < events[index - 1].timestamp) {
                throw new Error(`official ledger is not chronological at ${events[index].id}`);
            }
        }
        return events.reverse();
    }

    function parseOfficialLedger(text) {
        return normalizeLedgerRows(parseCsv(text));
    }

    function branchLabel(identifier) {
        return {
            southOffshore: 'South offshore',
            balutCentral: 'Balut central',
            glanMaasimNorth: 'Glan–Maasim north'
        }[identifier] || 'Unknown branch';
    }

    function currentLedgerFilters(documentRef) {
        const start = documentRef.getElementById('ledger-date-start');
        const end = documentRef.getElementById('ledger-date-end');
        const magnitude = documentRef.getElementById('ledger-magnitude-filter');
        const branch = documentRef.getElementById('ledger-branch-filter');
        return {
            startDate: start ? start.value : '',
            endDate: end ? end.value : '',
            minimumMagnitude: magnitude && magnitude.value ? Number(magnitude.value) : null,
            branch: branch ? branch.value : 'all'
        };
    }

    function filterLedgerEvents(events, filters) {
        return events.filter(event => {
            if (filters.startDate && event.datePht < filters.startDate) return false;
            if (filters.endDate && event.datePht > filters.endDate) return false;
            if (Number.isFinite(filters.minimumMagnitude) && event.magnitude < filters.minimumMagnitude) return false;
            if (filters.branch && filters.branch !== 'all' && event.branch !== filters.branch) return false;
            return true;
        });
    }

    function appendLedgerCell(documentRef, row, text, className) {
        const cell = createHtmlElement(documentRef, 'td', className, text);
        row.append(cell);
        return cell;
    }

    function renderOfficialLedger(documentRef) {
        if (ledgerState.status !== 'ready') return;
        const filters = currentLedgerFilters(documentRef);
        const filtered = filterLedgerEvents(ledgerState.events, filters);
        const pageCount = Math.max(1, Math.ceil(filtered.length / LEDGER_PAGE_SIZE));
        ledgerState.page = Math.min(Math.max(ledgerState.page, 1), pageCount);
        const startIndex = (ledgerState.page - 1) * LEDGER_PAGE_SIZE;
        const visible = filtered.slice(startIndex, startIndex + LEDGER_PAGE_SIZE);
        const body = documentRef.getElementById('official-ledger-body');
        if (body) {
            body.replaceChildren();
            visible.forEach(event => {
                const row = createHtmlElement(documentRef, 'tr');
                appendLedgerCell(documentRef, row, formatPht(event.timePht), 'mono');
                const magnitudeCell = appendLedgerCell(documentRef, row, `M${event.magnitude.toFixed(1)}`, 'mono official-ledger-magnitude');
                if (event.magnitude >= 5) magnitudeCell.classList.add('is-strong');
                appendLedgerCell(documentRef, row, `${event.depthKm.toFixed(0)} km`, 'mono');
                appendLedgerCell(documentRef, row, branchLabel(event.branch), 'official-ledger-branch');
                appendLedgerCell(documentRef, row, event.location, 'official-ledger-location');
                const sourceCell = createHtmlElement(documentRef, 'td');
                const link = createHtmlElement(documentRef, 'a', 'release-source-link', 'PHIVOLCS');
                link.setAttribute('href', event.bulletinUrl);
                link.setAttribute('target', '_blank');
                link.setAttribute('rel', 'noopener noreferrer');
                sourceCell.append(link);
                row.append(sourceCell);
                body.append(row);
            });
        }
        const firstVisible = filtered.length ? startIndex + 1 : 0;
        const lastVisible = Math.min(startIndex + visible.length, filtered.length);
        setText(documentRef, 'official-ledger-results',
            `${filtered.length} matching rows · showing ${firstVisible}–${lastVisible} · newest first`
        );
        setText(documentRef, 'official-ledger-page', `Page ${ledgerState.page} of ${pageCount}`);
        const previous = documentRef.getElementById('ledger-page-prev');
        const next = documentRef.getElementById('ledger-page-next');
        if (previous) previous.disabled = ledgerState.page <= 1;
        if (next) next.disabled = ledgerState.page >= pageCount;
    }

    function bindLedgerControls(documentRef) {
        if (ledgerState.filtersBound) return;
        const rerender = () => {
            ledgerState.page = 1;
            renderOfficialLedger(documentRef);
        };
        for (const id of ['ledger-date-start', 'ledger-date-end', 'ledger-magnitude-filter', 'ledger-branch-filter']) {
            const control = documentRef.getElementById(id);
            if (control) control.addEventListener('change', rerender);
        }
        const reset = documentRef.getElementById('ledger-filter-reset');
        if (reset) reset.addEventListener('click', () => {
            const start = documentRef.getElementById('ledger-date-start');
            const end = documentRef.getElementById('ledger-date-end');
            const magnitude = documentRef.getElementById('ledger-magnitude-filter');
            const branch = documentRef.getElementById('ledger-branch-filter');
            if (start) start.value = '';
            if (end) end.value = '';
            if (magnitude) magnitude.value = '';
            if (branch) branch.value = 'all';
            rerender();
        });
        const previous = documentRef.getElementById('ledger-page-prev');
        if (previous) previous.addEventListener('click', () => {
            ledgerState.page -= 1;
            renderOfficialLedger(documentRef);
        });
        const next = documentRef.getElementById('ledger-page-next');
        if (next) next.addEventListener('click', () => {
            ledgerState.page += 1;
            renderOfficialLedger(documentRef);
        });
        ledgerState.filtersBound = true;
    }

    function renderLedgerBlocked(documentRef, message) {
        ledgerState.status = 'blocked';
        const blocked = documentRef.getElementById('official-ledger-blocked');
        if (blocked) {
            blocked.hidden = false;
            blocked.textContent = `The official catalog could not be opened: ${message}. No rows have been substituted.`;
        }
        const content = documentRef.getElementById('official-ledger-content');
        if (content) content.hidden = true;
        const status = documentRef.getElementById('official-ledger-status');
        if (status) {
            status.textContent = 'Catalog unavailable';
            status.classList.add('is-blocked');
        }
    }

    async function loadLedger(documentRef, fetchImpl) {
        if (ledgerState.status === 'ready') {
            renderOfficialLedger(documentRef);
            return { ok: true, events: ledgerState.events };
        }
        if (ledgerState.promise) return ledgerState.promise;
        ledgerState.status = 'loading';
        const status = documentRef.getElementById('official-ledger-status');
        if (status) status.textContent = `Loading ${EXPECTED_EVENT_ROWS.toLocaleString()}-row PHIVOLCS snapshot…`;
        ledgerState.promise = (async () => {
            try {
                const response = await fetchImpl(EVENTS_URL, {
                    cache: 'no-cache',
                    credentials: 'same-origin',
                    headers: { Accept: 'text/csv' }
                });
                if (!response.ok) throw new Error(`catalog request returned HTTP ${response.status}`);
                const events = parseOfficialLedger(await response.text());
                ledgerState.events = events;
                ledgerState.status = 'ready';
                ledgerState.page = 1;
                bindLedgerControls(documentRef);
                const blocked = documentRef.getElementById('official-ledger-blocked');
                if (blocked) blocked.hidden = true;
                const content = documentRef.getElementById('official-ledger-content');
                if (content) content.hidden = false;
                if (status) {
                    status.textContent = 'Reviewed catalog loaded';
                    status.classList.add('is-ready');
                }
                renderOfficialLedger(documentRef);
                return { ok: true, events };
            } catch (error) {
                const message = error instanceof Error ? error.message : 'unknown catalog-loading failure';
                renderLedgerBlocked(documentRef, message);
                return { ok: false, errors: [message] };
            } finally {
                ledgerState.promise = null;
            }
        })();
        return ledgerState.promise;
    }

    function renderSequence(documentRef, summary) {
        const counts = summary.counts;
        const capture = summary.capture;
        const days = summary.dailyActivity;
        const firstSixFullDays = days.filter(day => day.datePht >= '2026-07-01' && day.datePht <= '2026-07-06');
        const laterFullDays = days.filter(day => day.datePht >= '2026-07-07' && day.datePht <= '2026-07-16');
        const peak = days.reduce((current, day) => day.eventCount > current.eventCount ? day : current, days[0]);

        setText(documentRef, 'sequence-verdict', summary.interpretation.standing);
        setText(documentRef, 'sequence-capture-time', formatPht(capture.capturedAtPht));
        setText(documentRef, 'sequence-coverage-start', formatPht(capture.coverageStartPht));
        setText(documentRef, 'sequence-last-event', formatPht(capture.lastIncludedEventPht));
        setText(documentRef, 'sequence-total-events', String(counts.officialPhivolcsRowsDeduplicated));
        setText(documentRef, 'sequence-m4-events', String(counts.m4AndAbove));
        setText(documentRef, 'sequence-m5-events', String(counts.m5AndAbove));
        setText(documentRef, 'sequence-m6-events', String(counts.m6AndAbove));
        setText(documentRef, 'sequence-activity-note',
            `Peak catalog activity was ${peak.eventCount} rows on ${formatDay(peak.datePht)}. `
            + `Full-day activity averaged ${average(firstSixFullDays).toFixed(1)} rows/day from Jul 1–6 and `
            + `${average(laterFullDays).toFixed(1)} rows/day from Jul 7–16.`
        );
        setText(documentRef, 'sequence-partial-note',
            `Jun 8 is a directly reviewed mainshock anchor. Jun 9–29 has no reviewed catalog coverage. `
            + `Continuous capture begins Jun 30 at 08:00 PHT; Jul 22 is partial at the ${formatPht(capture.capturedAtPht)} capture, `
            + `with the last included core-area row at ${formatPht(capture.lastIncludedEventPht)}.`
        );
        setText(documentRef, 'sequence-claim-boundary', summary.interpretation.claimBoundary);
        renderActivityChart(documentRef, days);
        renderReleases(documentRef, summary);
        renderMethod(documentRef, summary);

        const root = documentRef.getElementById('sequence-root');
        if (root) root.dataset.state = 'ready';
        const status = documentRef.getElementById('sequence-load-status');
        if (status) {
            status.textContent = 'Reviewed static snapshot loaded';
            status.classList.add('is-ready');
        }
    }

    function renderBlockedState(documentRef, errors) {
        const root = documentRef.getElementById('sequence-root');
        if (root) root.dataset.state = 'blocked';
        const status = documentRef.getElementById('sequence-load-status');
        if (status) {
            status.textContent = 'Sequence data unavailable';
            status.classList.remove('is-ready');
            status.classList.add('is-blocked');
        }
        const blocked = documentRef.getElementById('sequence-blocked-state');
        if (blocked) {
            blocked.hidden = false;
            blocked.textContent = `The reviewed sequence snapshot could not be rendered: ${errors.join('; ')}. No zero values or live state have been substituted.`;
        }
        const content = documentRef.getElementById('sequence-data-content');
        if (content) content.hidden = true;
    }

    async function loadSequence(documentRef, fetchImpl) {
        try {
            const response = await fetchImpl(SUMMARY_URL, {
                cache: 'no-cache',
                credentials: 'same-origin',
                headers: { Accept: 'application/json' }
            });
            if (!response.ok) throw new Error(`summary request returned HTTP ${response.status}`);
            const summary = await response.json();
            const errors = validateSummary(summary);
            if (errors.length) {
                renderBlockedState(documentRef, errors);
                return { ok: false, errors };
            }
            renderSequence(documentRef, summary);
            return { ok: true, summary };
        } catch (error) {
            const message = error instanceof Error ? error.message : 'unknown data-loading failure';
            renderBlockedState(documentRef, [message]);
            return { ok: false, errors: [message] };
        }
    }

    const api = {
        EXPECTED_DATASET_ID,
        SUMMARY_URL,
        EVENTS_URL,
        validateSummary,
        parseOfficialLedger,
        filterLedgerEvents,
        renderActivityChart,
        renderReleases,
        renderMethod,
        loadLedger,
        loadSequence
    };

    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    globalScope.TSRASequence = api;

    if (typeof document !== 'undefined' && typeof fetch === 'function') {
        const start = () => loadSequence(document, fetch.bind(globalScope));
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
        else start();
    }
}(typeof globalThis !== 'undefined' ? globalThis : this));
