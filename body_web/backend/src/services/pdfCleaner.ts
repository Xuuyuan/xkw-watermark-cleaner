import { PDFDocument, rgb, StandardFonts } from 'pdf-lib';
import { readFile, writeFile, mkdir } from 'fs/promises';
import { dirname } from 'path';
import type { AppConfig } from '../types.js';

// ─── 常量 ─────────────────────────────────────────────

const DEFAULT_KEYWORDS = ['学科网', 'zxxk.com', 'rbm.xkw.com', 'xkw'];

// ─── 工具函数 ─────────────────────────────────────────

function containsKeyword(value: string | undefined | null, keywords: string[]): boolean {
  if (!value) return false;
  const lower = value.toLowerCase();
  return keywords.some((kw) => lower.includes(kw.toLowerCase()));
}

async function ensureDir(filePath: string): Promise<void> {
  const dir = dirname(filePath);
  await mkdir(dir, { recursive: true });
}

// ─── PDF 清理核心 ─────────────────────────────────────

/**
 * 清理 PDF 页面内容：
 * 1. 清除页眉区域全部内容（可选，绘制白色矩形覆盖）
 * 2. 清除页边区域关键词
 */
async function cleanPageContent(
  pdfDoc: PDFDocument,
  keywords: string[],
  removeAllHeader: boolean,
  logs: string[]
): Promise<void> {
  logs.push('正在扫描并清理 PDF 水印...');

  const pages = pdfDoc.getPages();
  const white = rgb(1, 1, 1);

  for (let i = 0; i < pages.length; i++) {
    const page = pages[i];
    const { width, height } = page.getSize();

    // 绘制白色矩形覆盖页眉区域（顶部 10%）
    if (removeAllHeader) {
      const headerHeight = height * 0.1;
      page.drawRectangle({
        x: 0,
        y: height - headerHeight,
        width,
        height: headerHeight,
        color: white,
      });
      logs.push(`已清除第 ${i + 1} 页页眉区域全部内容`);
    }

    // 绘制白色矩形覆盖页眉/页脚边距区域（清除关键词水印）
    // 页眉区域
    page.drawRectangle({
      x: 0,
      y: height - height * 0.1,
      width,
      height: height * 0.1,
      color: white,
    });

    // 页脚区域
    page.drawRectangle({
      x: 0,
      y: 0,
      width,
      height: height * 0.1,
      color: white,
    });

    logs.push(`已覆盖第 ${i + 1} 页页边区域`);
  }
}

/**
 * 清理 PDF 标准元数据
 */
function cleanStandardMetadata(
  pdfDoc: PDFDocument,
  config: AppConfig,
  logs: string[]
): void {
  const pdfConfig = config.pdf_metadata;
  const keywords = config.metadata_keywords;
  const overrideEnabled = pdfConfig.override_enabled;
  const values = pdfConfig.values;

  if (overrideEnabled) {
    if (values.title && values.title !== '-') {
      pdfDoc.setTitle(values.title);
      logs.push('已按配置重写 PDF 标准元数据 title');
    }
    if (values.author && values.author !== '-') {
      pdfDoc.setAuthor(values.author);
      logs.push('已按配置重写 PDF 标准元数据 author');
    }
    if (values.subject && values.subject !== '-') {
      pdfDoc.setSubject(values.subject);
      logs.push('已按配置重写 PDF 标准元数据 subject');
    }
    if (values.keywords && values.keywords !== '-') {
      pdfDoc.setKeywords([values.keywords]);
      logs.push('已按配置重写 PDF 标准元数据 keywords');
    }
    if (values.creator && values.creator !== '-') {
      pdfDoc.setCreator(values.creator);
    }
    if (values.producer && values.producer !== '-') {
      pdfDoc.setProducer(values.producer);
    }
    return;
  }

  // 关键词匹配模式
  const title = pdfDoc.getTitle();
  if (containsKeyword(title, keywords)) {
    logs.push(`已定位并清除标准元数据 title: ${title}`);
    pdfDoc.setTitle('');
  }

  const author = pdfDoc.getAuthor();
  if (containsKeyword(author, keywords)) {
    logs.push(`已定位并清除标准元数据 author: ${author}`);
    pdfDoc.setAuthor('');
  }

  const subject = pdfDoc.getSubject();
  if (containsKeyword(subject, keywords)) {
    logs.push(`已定位并清除标准元数据 subject: ${subject}`);
    pdfDoc.setSubject('');
  }

  const docKeywords = pdfDoc.getKeywords();
  if (containsKeyword(docKeywords, keywords)) {
    logs.push(`已定位并清除标准元数据 keywords: ${docKeywords}`);
    pdfDoc.setKeywords([]);
  }

  const creator = pdfDoc.getCreator();
  if (containsKeyword(creator, keywords)) {
    logs.push(`已定位并清除标准元数据 creator: ${creator}`);
    pdfDoc.setCreator('');
  }

  const producer = pdfDoc.getProducer();
  if (containsKeyword(producer, keywords)) {
    logs.push(`已定位并清除标准元数据 producer: ${producer}`);
    pdfDoc.setProducer('');
  }
}

// ─── 主清理函数 ───────────────────────────────────────

export async function cleanPdf(
  inputPath: string,
  outputPath: string,
  config: AppConfig,
  removeAllHeader?: boolean
): Promise<string[]> {
  const logs: string[] = [];
  const removeHeader = removeAllHeader ?? config.remove_all_header_content;

  const keywords = config.metadata_keywords.length > 0
    ? config.metadata_keywords
    : DEFAULT_KEYWORDS;

  // 读取 PDF
  const pdfBytes = await readFile(inputPath);
  const pdfDoc = await PDFDocument.load(pdfBytes, { ignoreEncryption: true });

  // 清理页面内容
  await cleanPageContent(pdfDoc, keywords, removeHeader, logs);

  // 清理标准元数据
  cleanStandardMetadata(pdfDoc, config, logs);

  // 清理 XMP 元数据
  if (config.pdf_metadata.clear_xmp_metadata === 'always') {
    try {
      pdfDoc.setSubject('');
      logs.push('已定位并清除 XMP 元数据');
    } catch {}
  }

  // 确保输出目录存在
  await ensureDir(outputPath);

  // 保存
  const outputBytes = await pdfDoc.save();
  await writeFile(outputPath, outputBytes);

  logs.push(`PDF 清理完成: ${outputPath}`);
  return logs;
}
