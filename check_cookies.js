const fs = require('fs');
const files = fs.readdirSync('netflix');

let parsedCount = 0;
let failedCount = 0;

files.forEach(f => {
  const text = fs.readFileSync('netflix/' + f, 'utf8');
  const m1 = text.match(/(?:^|[\s\t;,'"\n])NetflixId[\s\t]*[=:\t ]\s*([^\s;'"\r\n]+)/i);
  const m2 = text.match(/(?:^|[\s\t;,'"\n])SecureNetflixId[\s\t]*[=:\t ]\s*([^\s;'"\r\n]+)/i);
  if (m1 || m2) {
    parsedCount++;
  } else {
    failedCount++;
    console.log('Failed file:', f);
  }
});

console.log('Total files in netflix folder:', files.length);
console.log('Successfully extracted NetflixId/SecureNetflixId:', parsedCount);
console.log('Failed:', failedCount);

