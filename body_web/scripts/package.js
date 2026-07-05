#!/usr/bin/env node
/**
 * 打包脚本：构建前后端并生成在线版 zip
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');

function run(cmd, cwd) {
  console.log(`\n> ${cmd}`);
  execSync(cmd, { cwd: cwd || ROOT, stdio: 'inherit' });
}

function main() {
  console.log('=== 构建前端 ===');
  run('npm install', path.join(ROOT, 'frontend'));
  run('npm run build', path.join(ROOT, 'frontend'));

  console.log('\n=== 构建后端 ===');
  run('npm install', path.join(ROOT, 'backend'));
  run('npm run build', path.join(ROOT, 'backend'));

  console.log('\n=== 打包完成 ===');
  console.log('  前端产物: frontend/dist/');
  console.log('  后端产物: backend/dist/');
  console.log('  启动方式: cd backend && npm start');
  console.log('  访问地址: http://localhost:3001');
}

main();
