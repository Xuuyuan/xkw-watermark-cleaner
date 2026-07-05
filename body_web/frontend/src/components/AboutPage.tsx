export function AboutPage() {
  return (
    <div className="about-page">
      <div className="icon">🛡️</div>
      <div className="title">学科网水印清理工具</div>
      <div className="version">版本 3.0 · 在线版 (Web)</div>
      <div className="desc">
        自动清理 DOC / DOCX / PDF 中的学科网相关水印<br />
        支持页眉页脚水印、动态标记、文档属性残留清除<br />
        浏览器直接使用，无需安装
      </div>
      <div className="tech">技术栈：React + TypeScript + Vite + Express + pdf-lib</div>
    </div>
  );
}
