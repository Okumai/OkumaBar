const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
function model(name) {
  const context = vm.createContext({});
  vm.runInContext(fs.readFileSync(path.join(root, 'plugins', 'okuma.dev_bar4omarchy.' + name, 'Model.js'), 'utf8'), context);
  return context;
}
const clock = model('clock');
assert.equal(clock.daysInYear(2024), 366);
assert.equal(clock.daysInYear(2025), 365);
assert.equal(clock.yearProgressPercent(2026, 11, 31), 100);
assert.equal(clock.nextClockFormat(['A', 'B'], 'A'), 'B');
assert.equal(clock.parseBirthYear(0, 2026), 0);
assert.equal(clock.isoWeek(2021, 0, 1), 53);
const weather = model('weather');
assert.equal(weather.shouldUseImperial('metric', 'en_US', 'United States'), false);
assert.equal(weather.shouldUseImperial('imperial', 'zh_CN', 'China'), true);
assert.equal(weather.wttrLocationQuery('New York', null, null), 'New%20York');
assert.equal(weather.parseGeocodingResults('null').length, 0);
assert.equal(weather.parseGeocodingResults('{bad').length, 0);
assert.equal(weather.parseGeocodingResults('x'.repeat(1048577)).length, 0);
assert.equal(weather.parseGeocodingResults(JSON.stringify({results: [{name:'Bad', latitude:100, longitude:0}]})).length, 0);
const markup = '<img src="https://example.invalid/tracker">';
const results = weather.parseGeocodingResults(JSON.stringify({results: Array.from({length: 10}, () => ({name: markup, country: markup, latitude:1, longitude:2}))}));
assert.equal(results.length, 5);
assert.equal(results[0].name, markup); // Keep data literal; QML must render it with Text.PlainText.
assert.ok(results[0].description.includes(markup));
assert.equal(weather.weatherResponseCompletesSave(true, 'open-meteo'), true);
console.log('Clock/weather model regression tests passed.');
