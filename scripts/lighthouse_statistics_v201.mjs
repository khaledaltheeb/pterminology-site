export function median(values) {
  if (!Array.isArray(values) || values.length === 0) {
    throw new TypeError('median requires at least one numeric value');
  }
  const numbers = values.map((value) => {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      throw new TypeError(`median received a non-finite value: ${value}`);
    }
    return value;
  }).sort((a, b) => a - b);
  const middle = Math.floor(numbers.length / 2);
  return numbers.length % 2 === 1
    ? numbers[middle]
    : (numbers[middle - 1] + numbers[middle]) / 2;
}

export function normalizeOddSampleCount(raw, fallback = 3) {
  const parsed = Number.parseInt(String(raw ?? ''), 10);
  if (!Number.isInteger(parsed) || parsed < 1) return fallback;
  return parsed % 2 === 1 ? parsed : parsed + 1;
}

function completeFiniteValues(samples, key) {
  const values = samples.map((sample) => sample[key]);
  return values.every((value) => typeof value === 'number' && Number.isFinite(value))
    ? values
    : null;
}

export function aggregateLighthouseSamples(samples) {
  if (!Array.isArray(samples) || samples.length === 0) {
    throw new TypeError('aggregateLighthouseSamples requires at least one sample');
  }
  const route = samples[0].route;
  const formFactor = samples[0].formFactor;
  if (samples.some((sample) => sample.route !== route || sample.formFactor !== formFactor)) {
    throw new TypeError('all Lighthouse samples must share route and formFactor');
  }

  const medianKeys = [
    'performance',
    'fcp',
    'lcp',
    'cls',
    'tbt',
    'speedIndex',
    'interactive',
    'totalByteWeight',
    'unusedJavascript',
    'unusedCss'
  ];
  const strictMinimumKeys = ['accessibility', 'bestPractices', 'seo'];
  const aggregated = {
    route,
    formFactor,
    sampleCount: samples.length,
    aggregation: 'median-lab-strict-quality-minimum'
  };
  for (const key of medianKeys) {
    const values = completeFiniteValues(samples, key);
    aggregated[key] = values ? median(values) : null;
  }
  for (const key of strictMinimumKeys) {
    const values = completeFiniteValues(samples, key);
    aggregated[key] = values ? Math.min(...values) : null;
  }
  return aggregated;
}
