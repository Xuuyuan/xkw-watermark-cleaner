import AdmZip from 'adm-zip';
import { DOMParser, XMLSerializer } from '@xmldom/xmldom';
import xpath from 'xpath';
import { join } from 'path';
import { readFile, writeFile, mkdir } from 'fs/promises';
import type { AppConfig } from '../types.js';

// ─── 常量 ─────────────────────────────────────────────

const HEADER_FOOTER_KEYWORDS = ['学科网', 'zxxk.com', '北京）股份有限公司'];
const BODY_TEXT_KEYWORDS = [
  'zxxk.com',
  '学科网（北京）股份有限公司',
  '学科网(北京)股份有限公司',
  '北京）股份有限公司',
];
const METADATA_KEYWORDS = ['学科网', 'zxxk.com', 'rbm.xkw.com', 'xkw'];
const BODY_DRAWING_KEYWORDS = ['学科网', 'zxxk.com', 'rbm.xkw.com', 'xkw'];

// OOXML 命名空间
const NS = {
  w: 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
  cp: 'http://schemas.openxmlformats.org/officeDocument/2006/custom-properties',
  dc: 'http://purl.org/dc/elements/1.1/',
  dcterms: 'http://purl.org/dc/terms/',
  xsi: 'http://www.w3.org/2001/XMLSchema-instance',
};

// 微小元素阈值 (EMU: English Metric Unit, 914400 EMU = 1 inch)
// 0.2 inch = 182880 EMU
const SIZE_THRESHOLD = 182880;

// ─── 工具函数 ─────────────────────────────────────────

function hasKeywordText(text: string, keywords: string[]): boolean {
  const lower = text.toLowerCase();
  return keywords.some((kw) => lower.includes(kw.toLowerCase()));
}

function firstMatchedKeyword(text: string, keywords: string[]): string | null {
  const lower = text.toLowerCase();
  for (const kw of keywords) {
    if (lower.includes(kw.toLowerCase())) return kw;
  }
  return null;
}

/** 获取元素的本地名（去掉命名空间前缀） */
function localName(node: Node): string {
  const name = node.nodeName || '';
  return name.includes(':') ? name.split(':').slice(1).join(':') : name;
}

/** 查找所有指定本地名的后代元素 */
function findElementsByLocalName(parent: Node, name: string): Element[] {
  const result: Element[] = [];
  const walk = (node: Node) => {
    if (node.nodeType === 1) {
      const el = node as Element;
      if (localName(el) === name) result.push(el);
    }
    for (let i = 0; i < node.childNodes.length; i++) {
      walk(node.childNodes[i]);
    }
  };
  walk(parent);
  return result;
}

/** 判断元素是否微小（水印特征） */
function isTinyElement(element: Element): boolean {
  try {
    const extents = findElementsByLocalName(element, 'extent');
    for (const ext of extents) {
      const cx = parseInt(ext.getAttribute('cx') || '0', 10);
      const cy = parseInt(ext.getAttribute('cy') || '0', 10);
      if (cx > 0 && cx < SIZE_THRESHOLD && cy > 0 && cy < SIZE_THRESHOLD) {
        return true;
      }
    }
  } catch {
    return false;
  }
  return false;
}

/** 判断元素是否包含目标关键词或微小 */
function isTargetElement(element: Element, keywords?: string[]): boolean {
  try {
    const xmlStr = new XMLSerializer().serializeToString(element);
    if (keywords && hasKeywordText(xmlStr, keywords)) return true;
  } catch {
    return false;
  }
  return isTinyElement(element);
}

/** 移除元素 */
function removeElement(element: Element): void {
  const parent = element.parentNode;
  if (parent) {
    parent.removeChild(element);
  }
}

/** 清洗 descr/title 属性中的关键词 */
function scrubDescrAttributes(element: Element, keywords: string[], label: string): void {
  const walk = (node: Node) => {
    if (node.nodeType === 1) {
      const el = node as Element;
      for (const attr of ['descr', 'title']) {
        const val = el.getAttribute(attr);
        if (val && hasKeywordText(val, keywords)) {
          el.setAttribute(attr, '');
        }
      }
    }
    for (let i = 0; i < node.childNodes.length; i++) {
      walk(node.childNodes[i]);
    }
  };
  walk(element);
}

/** 获取元素的纯文本内容 */
function getElementText(element: Node): string {
  let text = '';
  const walk = (node: Node) => {
    if (node.nodeType === 3) {
      text += node.nodeValue || '';
    }
    for (let i = 0; i < node.childNodes.length; i++) {
      walk(node.childNodes[i]);
    }
  };
  walk(element);
  return text;
}

// ─── DOCX 清理核心 ────────────────────────────────────

interface CleanResult {
  logs: string[];
}

/** 清理页眉/页脚容器中的水印 */
function cleanHeaderFooterContainer(
  container: Document,
  label: string,
  logs: string[]
): void {
  // 清理 drawing 元素
  const drawings = findElementsByLocalName(container.documentElement, 'drawing');
  for (const drawing of drawings) {
    if (isTargetElement(drawing, HEADER_FOOTER_KEYWORDS)) {
      removeElement(drawing);
      logs.push(`已定位并清除${label}绘图对象水印`);
    }
  }

  // 清理 shape 元素
  const shapes = findElementsByLocalName(container.documentElement, 'shape');
  for (const shape of shapes) {
    if (isTargetElement(shape, HEADER_FOOTER_KEYWORDS)) {
      removeElement(shape);
      logs.push(`已定位并清除${label}形状对象水印`);
    }
  }

  // 清理含关键词的段落文本
  const paragraphs = findElementsByLocalName(container.documentElement, 'p');
  for (const p of paragraphs) {
    const text = getElementText(p);
    if (hasKeywordText(text, HEADER_FOOTER_KEYWORDS)) {
      logs.push(`已定位并清除${label}文本水印: ${text.trim()}`);
      // 清空段落中的所有文本节点
      const runs = findElementsByLocalName(p, 'r');
      for (const r of runs) {
        const ts = findElementsByLocalName(r, 't');
        for (const t of ts) {
          t.textContent = '';
        }
      }
    }
  }
}

/** 清空页眉/页脚全部内容，保留一个空段落 */
function clearContainerAll(container: Document, label: string, logs: string[]): void {
  const root = container.documentElement;
  const children = Array.from(root.childNodes).filter((n) => n.nodeType === 1);

  if (children.length === 0) return;

  const hasText = getElementText(root).trim().length > 0;
  const hasDrawings = findElementsByLocalName(root, 'drawing').length > 0;
  const hasShapes = findElementsByLocalName(root, 'shape').length > 0;
  const hasTables = findElementsByLocalName(root, 'tbl').length > 0;

  if (!hasText && !hasDrawings && !hasShapes && !hasTables) return;

  // 移除所有子元素
  const toRemove = Array.from(root.childNodes);
  for (const child of toRemove) {
    root.removeChild(child);
  }

  // 添加一个空段落 <w:p/>
  const nsUri = NS.w;
  const emptyP = container.createElementNS(nsUri, 'w:p');
  root.appendChild(emptyP);

  logs.push(`已清空${label}全部内容`);
}

/** 清理正文段落 */
function cleanBodyParagraph(paragraph: Element, index: number, logs: string[]): void {
  // 清理 drawing
  const drawings = findElementsByLocalName(paragraph, 'drawing');
  for (const drawing of drawings) {
    if (isTinyElement(drawing)) {
      removeElement(drawing);
      logs.push(`已定位并清除正文段落 ${index} 中的微小绘图水印`);
    } else {
      scrubDescrAttributes(drawing, BODY_DRAWING_KEYWORDS, `正文段落 ${index}`);
    }
  }

  // 清理 shape
  const shapes = findElementsByLocalName(paragraph, 'shape');
  for (const shape of shapes) {
    if (isTinyElement(shape)) {
      removeElement(shape);
      logs.push(`已定位并清除正文段落 ${index} 中的微小形状水印`);
    } else {
      scrubDescrAttributes(shape, BODY_DRAWING_KEYWORDS, `正文段落 ${index}`);
    }
  }

  // 清理文本水印
  const text = getElementText(paragraph);
  if (hasKeywordText(text, BODY_TEXT_KEYWORDS)) {
    logs.push(`已定位并清除正文段落 ${index} 文本水印: ${text.trim()}`);
    const runs = findElementsByLocalName(paragraph, 'r');
    for (const r of runs) {
      const ts = findElementsByLocalName(r, 't');
      for (const t of ts) {
        t.textContent = '';
      }
    }
  }
}

/** 清理核心属性 (docProps/core.xml) */
function cleanCoreProperties(
  coreDoc: Document,
  config: AppConfig,
  logs: string[]
): void {
  try {
    const coreConfig = config.docx_core_properties;
    const keywords = config.metadata_keywords;
    const overrideEnabled = coreConfig.override_enabled;
    const values = coreConfig.values;

    // 属性名 -> XML 元素名映射
    const propMap: Record<string, string> = {
      author: 'dc:creator',
      comments: 'cp:comments',
      title: 'dc:title',
      subject: 'dc:subject',
      keywords: 'cp:keywords',
    };

    for (const [propName, elemName] of Object.entries(propMap)) {
      const elems = coreDoc.getElementsByTagName(elemName);
      const elem = elems.item(0);
      const currentValue = elem?.textContent || '';

      if (overrideEnabled) {
        const configuredValue = values[propName as keyof typeof values] || '';
        if (configuredValue === '-') continue;
        if (elem && currentValue !== configuredValue) {
          logs.push(`已按配置重写核心属性 ${propName}: ${currentValue}`);
          elem.textContent = configuredValue;
        }
        continue;
      }

      const matched = firstMatchedKeyword(currentValue, keywords);
      if (matched && elem) {
        logs.push(`已定位并清除核心属性 ${propName}: ${currentValue}，命中关键词: ${matched}`);
        elem.textContent = '';
      }
    }
  } catch {
    // 忽略错误
  }
}

/** 清理自定义属性 (docProps/custom.xml) */
function cleanCustomProperties(
  customDoc: Document,
  keywords: string[],
  logs: string[]
): void {
  const properties = customDoc.getElementsByTagName('cp:property');
  const toRemove: Element[] = [];

  for (let i = 0; i < properties.length; i++) {
    const prop = properties.item(i)!;
    const text = getElementText(prop);
    if (hasKeywordText(text, keywords)) {
      logs.push(`已定位并清除自定义属性 ${prop.getAttribute('name')}: ${text.trim()}`);
      toRemove.push(prop);
    }
  }

  for (const prop of toRemove) {
    prop.parentNode?.removeChild(prop);
  }
}

// ─── 主清理函数 ───────────────────────────────────────

export async function cleanDocx(
  inputPath: string,
  outputPath: string,
  config: AppConfig,
  removeAllHeader?: boolean
): Promise<string[]> {
  const logs: string[] = [];
  const removeHeader = removeAllHeader ?? config.remove_all_header_content;

  logs.push('正在扫描并清理 DOCX 水印...');

  // 读取 docx (ZIP)
  const zip = new AdmZip(inputPath);

  // 找到所有需要处理的 XML 文件
  const entries = zip.getEntries();

  // 处理页眉/页脚文件
  const headerFooterFiles = entries.filter(
    (e) => /word\/(header|footer)\d*\.xml$/.test(e.entryName)
  );

  for (const entry of headerFooterFiles) {
    const isHeader = /header/.test(entry.entryName);
    const label = entry.entryName.replace('word/', '').replace('.xml', '');
    const xmlContent = entry.getData().toString('utf-8');
    const doc = new DOMParser().parseFromString(xmlContent, 'text/xml');

    if (removeHeader && isHeader) {
      clearContainerAll(doc, label, logs);
    } else {
      cleanHeaderFooterContainer(doc, label, logs);
    }

    const serializer = new XMLSerializer();
    const newXml = serializer.serializeToString(doc);
    zip.updateFile(entry.entryName, Buffer.from(newXml, 'utf-8'));
  }

  // 处理正文 document.xml
  const docEntry = entries.find((e) => e.entryName === 'word/document.xml');
  if (docEntry) {
    const xmlContent = docEntry.getData().toString('utf-8');
    const doc = new DOMParser().parseFromString(xmlContent, 'text/xml');

    // 清理正文段落
    const paragraphs = findElementsByLocalName(doc.documentElement, 'p');
    paragraphs.forEach((p, i) => cleanBodyParagraph(p, i + 1, logs));

    const serializer = new XMLSerializer();
    const newXml = serializer.serializeToString(doc);
    zip.updateFile('word/document.xml', Buffer.from(newXml, 'utf-8'));
  }

  // 处理核心属性 docProps/core.xml
  const coreEntry = entries.find((e) => e.entryName === 'docProps/core.xml');
  if (coreEntry) {
    const xmlContent = coreEntry.getData().toString('utf-8');
    const doc = new DOMParser().parseFromString(xmlContent, 'text/xml');
    cleanCoreProperties(doc, config, logs);
    const serializer = new XMLSerializer();
    const newXml = serializer.serializeToString(doc);
    zip.updateFile('docProps/core.xml', Buffer.from(newXml, 'utf-8'));
  }

  // 处理自定义属性 docProps/custom.xml
  const customEntry = entries.find((e) => e.entryName === 'docProps/custom.xml');
  if (customEntry) {
    const xmlContent = customEntry.getData().toString('utf-8');
    const doc = new DOMParser().parseFromString(xmlContent, 'text/xml');
    cleanCustomProperties(doc, METADATA_KEYWORDS, logs);
    const serializer = new XMLSerializer();
    const newXml = serializer.serializeToString(doc);
    zip.updateFile('docProps/custom.xml', Buffer.from(newXml, 'utf-8'));
  }

  // 写入输出文件
  const outputDir = outputPath.includes('\\') || outputPath.includes('/')
    ? outputPath.replace(/[\\/][^\\/]+$/, '')
    : '.';
  await mkdir(outputDir, { recursive: true });

  zip.writeZip(outputPath);

  logs.push(`DOCX 清理完成: ${outputPath}`);
  return logs;
}
