// Forensic Decoding & Human-Readable Formatter Utilities
export interface DecodedValue {
  type: 'timestamp' | 'json' | 'blob' | 'hex_text' | 'base64_text' | 'boolean' | 'filesize' | 'text' | 'number' | 'null';
  display: string;
  badge?: string;
  badgeColor?: string;
  rawValue: any;
  details?: {
    utcDate?: string;
    localDate?: string;
    isoDate?: string;
    relativeTime?: string;
    epoch?: number | string;
    timestampFormat?: string;
    parsedJson?: any;
    formattedJson?: string;
    blobTag?: string;
    blobSize?: number;
    blobMime?: string;
    isImage?: boolean;
    base64?: string;
    hexDump?: string;
    decodedText?: string;
  };
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export function getRelativeTime(d: Date): string {
  const diffSec = Math.round((Date.now() - d.getTime()) / 1000);
  if (Math.abs(diffSec) < 60) return `${diffSec >= 0 ? diffSec : -diffSec}s ago`;
  const diffMin = Math.round(diffSec / 60);
  if (Math.abs(diffMin) < 60) return `${diffMin}m ago`;
  const diffHour = Math.round(diffMin / 60);
  if (Math.abs(diffHour) < 24) return `${diffHour}h ago`;
  const diffDay = Math.round(diffHour / 24);
  if (Math.abs(diffDay) < 30) return `${diffDay}d ago`;
  const diffMonth = Math.round(diffDay / 30);
  if (Math.abs(diffMonth) < 12) return `${diffMonth}mo ago`;
  const diffYear = Math.round(diffDay / 365);
  return `${diffYear}y ago`;
}

export function generateHexDump(hexStr: string, limit = 256): string {
  const cleanHex = hexStr.replace(/[^0-9a-fA-F]/g, '');
  const bytes: number[] = [];
  for (let i = 0; i < Math.min(cleanHex.length, limit * 2); i += 2) {
    bytes.push(parseInt(cleanHex.substr(i, 2), 16));
  }
  const lines: string[] = [];
  for (let i = 0; i < bytes.length; i += 16) {
    const chunk = bytes.slice(i, i + 16);
    const offset = i.toString(16).toUpperCase().padStart(8, '0');
    const hexPart = chunk.map((b) => b.toString(16).toUpperCase().padStart(2, '0')).join(' ').padEnd(48, ' ');
    const asciiPart = chunk.map((b) => (b >= 32 && b <= 126 ? String.fromCharCode(b) : '.')).join('');
    lines.push(`${offset}  ${hexPart}  |${asciiPart}|`);
  }
  return lines.join('\n');
}

export function decodeCell(val: any, colName = ''): DecodedValue {
  if (val === null || val === undefined) {
    return { type: 'null', display: 'null', rawValue: val };
  }

  // Handle backend serialized BLOB object
  if (typeof val === 'object' && val.__type__ === 'blob') {
    const isImage = Boolean(val.mime && val.mime.startsWith('image/'));
    const hexDump = val.hex ? generateHexDump(val.hex) : '';
    return {
      type: 'blob',
      display: isImage ? `🖼️ ${val.tag} (${formatBytes(val.size)})` : `📦 ${val.tag} (${formatBytes(val.size)})`,
      badge: val.tag,
      badgeColor: isImage
        ? 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40'
        : 'text-purple-400 bg-purple-950/40 border-purple-800/40',
      rawValue: val,
      details: {
        blobTag: val.tag,
        blobSize: val.size,
        blobMime: val.mime,
        isImage,
        base64: val.base64,
        hexDump,
      },
    };
  }

  const colLower = colName.toLowerCase();
  const isDateCol = /date|time|created|modified|updated|timestamp|expires|sent|received|epoch|last_visit|scheduled|arrival/i.test(colLower);

  // Number decoding
  if (typeof val === 'number') {
    let detectedDate: Date | null = null;
    let formatName = '';

    // Standard Unix seconds (e.g. 946684800 to 2500000000 -> 2000 to 2049)
    if (val >= 946684800 && val <= 2500000000) {
      detectedDate = new Date(val * 1000);
      formatName = 'Unix Epoch (Seconds)';
    }
    // Unix milliseconds (e.g. 946684800000 to 2500000000000)
    else if (val >= 946684800000 && val <= 2500000000000) {
      detectedDate = new Date(val);
      formatName = 'Unix Epoch (Milliseconds)';
    }
    // Unix microseconds (e.g. 946684800000000 to 2500000000000000)
    else if (val >= 946684800000000 && val <= 2500000000000000) {
      detectedDate = new Date(Math.floor(val / 1000));
      formatName = 'Unix Epoch (Microseconds)';
    }
    // Apple Mac Cocoa CoreData absolute time (seconds since 2001-01-01)
    else if (isDateCol && val >= 100000000 && val <= 1500000000) {
      detectedDate = new Date((val + 978307200) * 1000);
      formatName = 'Apple Mac Cocoa Absolute Time';
    }
    // Chrome / WebKit microsecond timestamps (17 digits, starts with 13...)
    else if (val >= 12000000000000000 && val <= 15000000000000000) {
      detectedDate = new Date(Math.floor(val / 1000) - 11644473600000);
      formatName = 'Chrome/WebKit Microseconds';
    }
    // Windows FileTime (100-nanoseconds since 1601-01-01, typically 17-18 digits, e.g. 133336161230286775)
    else if (val >= 116444736000000000 && val <= 160000000000000000) {
      const unixSec = (val - 116444736000000000) / 10000000;
      detectedDate = new Date(unixSec * 1000);
      formatName = 'Windows FileTime (100ns)';
    }

    if (detectedDate && !isNaN(detectedDate.getTime())) {
      const utcDate = detectedDate.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
      const localDate = detectedDate.toLocaleString();
      const isoDate = detectedDate.toISOString();
      const relativeTime = getRelativeTime(detectedDate);
      return {
        type: 'timestamp',
        display: utcDate,
        badge: 'Timestamp',
        badgeColor: 'text-cyan-400 bg-cyan-950/40 border-cyan-800/40',
        rawValue: val,
        details: {
          utcDate,
          localDate,
          isoDate,
          relativeTime,
          epoch: val,
          timestampFormat: formatName,
        },
      };
    }

    // Boolean / Status flag
    if (
      (val === 0 || val === 1) &&
      (colLower.startsWith('is_') ||
        colLower.startsWith('has_') ||
        colLower.startsWith('can_') ||
        ['read', 'deleted', 'starred', 'pinned', 'archived', 'active', 'enabled', 'verified'].includes(colLower))
    ) {
      return {
        type: 'boolean',
        display: val === 1 ? '1 (True / Yes)' : '0 (False / No)',
        badge: val === 1 ? 'TRUE' : 'FALSE',
        badgeColor:
          val === 1 ? 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40' : 'text-slate-400 bg-[#162030] border-[#223145]',
        rawValue: val,
      };
    }

    // File size / length
    if (/(file_?)?size|bytes|filesize|length_bytes/i.test(colLower) && val > 0) {
      return {
        type: 'filesize',
        display: `${val} (${formatBytes(val)})`,
        badge: formatBytes(val),
        badgeColor: 'text-blue-400 bg-blue-950/40 border-blue-800/40',
        rawValue: val,
      };
    }

    return { type: 'number', display: String(val), rawValue: val };
  }

  // String decoding
  if (typeof val === 'string') {
    const trimmed = val.trim();

    // 1. JSON String
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        const parsed = JSON.parse(trimmed);
        const count = Array.isArray(parsed) ? `${parsed.length} items` : `${Object.keys(parsed).length} keys`;
        return {
          type: 'json',
          display: `JSON (${count})`,
          badge: `JSON (${count})`,
          badgeColor: 'text-amber-400 bg-amber-950/40 border-amber-800/40',
          rawValue: val,
          details: {
            parsedJson: parsed,
            formattedJson: JSON.stringify(parsed, null, 2),
          },
        };
      } catch {}
    }

    // 2. String representation of Epoch Timestamps
    if (/^\d{10,18}$/.test(trimmed)) {
      const numVal = parseInt(trimmed, 10);
      return decodeCell(numVal, colName);
    }
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(trimmed)) {
      const d = new Date(trimmed);
      if (!isNaN(d.getTime())) {
        const utcDate = d.toISOString().replace('T', ' ').replace(/\.\d+Z$/, ' UTC');
        return {
          type: 'timestamp',
          display: utcDate,
          badge: 'ISO Date',
          badgeColor: 'text-cyan-400 bg-cyan-950/40 border-cyan-800/40',
          rawValue: val,
          details: {
            utcDate,
            localDate: d.toLocaleString(),
            isoDate: d.toISOString(),
            relativeTime: getRelativeTime(d),
            epoch: d.getTime(),
            timestampFormat: 'ISO-8601 String',
          },
        };
      }
    }

    // 3. Hex Encoded String
    const hexCandidate = trimmed.startsWith('0x') ? trimmed.slice(2) : trimmed;
    if (/^[0-9a-fA-F]{8,}$/.test(hexCandidate) && hexCandidate.length % 2 === 0) {
      try {
        let ascii = '';
        let isAllPrintable = true;
        for (let i = 0; i < Math.min(hexCandidate.length, 120); i += 2) {
          const code = parseInt(hexCandidate.substr(i, 2), 16);
          if (code >= 32 && code <= 126) {
            ascii += String.fromCharCode(code);
          } else {
            isAllPrintable = false;
            break;
          }
        }
        if (isAllPrintable && ascii.length >= 4) {
          return {
            type: 'hex_text',
            display: `"${ascii}"`,
            badge: 'HEX Decoded',
            badgeColor: 'text-pink-400 bg-pink-950/40 border-pink-800/40',
            rawValue: val,
            details: {
              decodedText: ascii,
              hexDump: generateHexDump(hexCandidate),
            },
          };
        }
      } catch {}
    }

    // 4. Base64 Encoded String
    if (/^[A-Za-z0-9+/=]{12,}$/.test(trimmed) && trimmed.length % 4 === 0 && !trimmed.includes(' ')) {
      try {
        const decoded = atob(trimmed);
        let isPrintable = true;
        for (let i = 0; i < Math.min(decoded.length, 100); i++) {
          const c = decoded.charCodeAt(i);
          if (c < 32 && c !== 10 && c !== 13 && c !== 9) {
            isPrintable = false;
            break;
          }
        }
        if (isPrintable && decoded.length >= 4) {
          return {
            type: 'base64_text',
            display: `"${decoded.slice(0, 60)}"`,
            badge: 'Base64 Decoded',
            badgeColor: 'text-indigo-400 bg-indigo-950/40 border-indigo-800/40',
            rawValue: val,
            details: {
              decodedText: decoded,
              base64: trimmed,
            },
          };
        }
      } catch {}
    }

    // Standard text string
    return {
      type: 'text',
      display: val,
      rawValue: val,
    };
  }

  return { type: 'text', display: String(val), rawValue: val };
}
