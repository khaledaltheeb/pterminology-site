import test from 'node:test';
import assert from 'node:assert/strict';

import {
  aggregateLighthouseSamples,
  median,
  normalizeOddSampleCount
} from '../scripts/lighthouse_statistics_v201.mjs';

test('median rejects empty and non-finite values', () => {
  assert.throws(() => median([]), /at least one/);
  assert.throws(() => median([1, Number.NaN, 3]), /non-finite/);
});

test('median handles odd and even samples deterministically', () => {
  assert.equal(median([844, 538, 560]), 560);
  assert.equal(median([10, 40, 20, 30]), 25);
});

test('sample count is always positive and odd', () => {
  assert.equal(normalizeOddSampleCount(undefined), 3);
  assert.equal(normalizeOddSampleCount('0'), 3);
  assert.equal(normalizeOddSampleCount('2'), 3);
  assert.equal(normalizeOddSampleCount('5'), 5);
});

test('one noisy TBT sample does not override the median', () => {
  const base = {
    route: '',
    formFactor: 'mobile',
    performance: 0.86,
    accessibility: 1,
    bestPractices: 1,
    seo: 1,
    fcp: 1300,
    lcp: 1450,
    cls: 0,
    speedIndex: 1500,
    interactive: 2200,
    totalByteWeight: 29766,
    unusedJavascript: 0,
    unusedCss: 0
  };
  const result = aggregateLighthouseSamples([
    { ...base, tbt: 538 },
    { ...base, tbt: 844, performance: 0.80 },
    { ...base, tbt: 560, performance: 0.85 }
  ]);
  assert.equal(result.sampleCount, 3);
  assert.equal(result.aggregation, 'median');
  assert.equal(result.tbt, 560);
  assert.equal(result.performance, 0.85);
  assert.equal(result.totalByteWeight, 29766);
});

test('samples from different routes cannot be aggregated', () => {
  const sample = {
    route: '', formFactor: 'mobile', performance: 1, accessibility: 1,
    bestPractices: 1, seo: 1, fcp: 1, lcp: 1, cls: 0, tbt: 0,
    speedIndex: 1, interactive: 1, totalByteWeight: 1,
    unusedJavascript: 0, unusedCss: 0
  };
  assert.throws(
    () => aggregateLighthouseSamples([sample, { ...sample, route: 'tips/' }]),
    /share route and formFactor/
  );
});
