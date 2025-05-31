const fs = require('fs');
const path = require('path');

const pagesDir = path.join(__dirname, '../src/pages');
const files = fs.readdirSync(pagesDir).filter(f => f.endsWith('.jsx'));

files.forEach(file => {
  const filePath = path.join(pagesDir, file);
  const content = fs.readFileSync(filePath, 'utf-8');
  if (!/export default/.test(content)) {
    const name = path.basename(file, '.jsx');
    const placeholder = `import React from "react";\n\nexport default function ${name}() {\n  return <div>${name} Page (Auto-generated Placeholder)</div>;\n}\n`;
    fs.writeFileSync(filePath, placeholder);
    console.log(`Patched missing export in ${file}`);
  }
}); 