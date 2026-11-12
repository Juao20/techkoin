import { deflateSync } from 'node:zlib'

function crc32(buf: Buffer): number {
  let c = ~0
  for (const byte of buf) {
    c ^= byte
    for (let k = 0; k < 8; k++) c = (c >>> 1) ^ (0xedb88320 & -(c & 1))
  }
  return ~c >>> 0
}

function chunk(type: string, data: Buffer): Buffer {
  const length = Buffer.alloc(4)
  length.writeUInt32BE(data.length)
  const body = Buffer.concat([Buffer.from(type), data])
  const crc = Buffer.alloc(4)
  crc.writeUInt32BE(crc32(body))
  return Buffer.concat([length, body, crc])
}

/** A 32x32 PNG of random pixels: every call gives a different perceptual hash. */
export function randomPng(): Buffer {
  const size = 32
  const raw = Buffer.alloc((size * 3 + 1) * size)
  for (let y = 0; y < size; y++) {
    raw[y * (size * 3 + 1)] = 0
    for (let i = 1; i <= size * 3; i++)
      raw[y * (size * 3 + 1) + i] = Math.floor(Math.random() * 256)
  }
  const header = Buffer.alloc(13)
  header.writeUInt32BE(size, 0)
  header.writeUInt32BE(size, 4)
  header[8] = 8 // bit depth
  header[9] = 2 // RGB
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', header),
    chunk('IDAT', deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0)),
  ])
}

/** A random 15 digit IMEI with a valid Luhn check digit. */
export function randomImei(): string {
  const body = '35' + Array.from({ length: 12 }, () => Math.floor(Math.random() * 10)).join('')
  let total = 0
  ;[...body].reverse().forEach((ch, i) => {
    let n = Number(ch)
    if (i % 2 === 0) {
      n *= 2
      if (n > 9) n -= 9
    }
    total += n
  })
  return body + String((10 - (total % 10)) % 10)
}
