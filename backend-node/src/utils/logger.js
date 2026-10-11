const fs = require('fs');
const path = require('path');

const logsDir = path.join(__dirname, '..', '..', 'logs');
fs.mkdirSync(logsDir, { recursive: true });

const logFile = path.join(logsDir, 'backend.log');

function formatTimestamp() {
  return new Date().toISOString();
}

function serializeMeta(meta) {
  if (meta === undefined || meta === null) return '';
  if (typeof meta === 'string') return meta;

  try {
    return JSON.stringify(meta);
  } catch (error) {
    return String(meta);
  }
}

function write(level, message, meta) {
  const details = serializeMeta(meta);
  const output = details ? `[${formatTimestamp()}] [${level}] ${message} ${details}` : `[${formatTimestamp()}] [${level}] ${message}`;
  fs.appendFileSync(logFile, `${output}\n`, 'utf8');
  console.log(output);
}

module.exports = {
  info(message, meta) {
    write('INFO', message, meta);
  },
  warn(message, meta) {
    write('WARN', message, meta);
  },
  error(message, meta) {
    write('ERROR', message, meta);
  },
  logFile,
};
