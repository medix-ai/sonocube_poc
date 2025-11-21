"""
PDF 리포트 생성 모듈
ReportLab 기반 리포트 생성
"""
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib import colors

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg


def build_pdf(report_path: Path, analysis_result: Dict[str, Any]):
    """
    분석 결과를 PDF 리포트로 생성
    
    Args:
        report_path: 저장할 PDF 파일 경로
        analysis_result: analyze_clip()의 결과 딕셔너리
    """
    doc = SimpleDocTemplate(str(report_path), pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # 제목 스타일
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # 제목
    title = Paragraph("SonoCube PoC - Cardiac Echo Analysis Report", title_style)
    story.append(title)
    story.append(Spacer(1, 0.5*cm))
    
    # 날짜/시간
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_para = Paragraph(f"<b>Generated:</b> {date_str}", styles['Normal'])
    story.append(date_para)
    story.append(Spacer(1, 0.5*cm))
    
    # 메트릭 섹션
    story.append(Paragraph("<b>Analysis Results</b>", styles['Heading2']))
    story.append(Spacer(1, 0.3*cm))
    
    # 메트릭 테이블
    ef = analysis_result.get("ef", 0.0)
    volume_info = analysis_result.get("volume_info", {})
    edv = volume_info.get("edv", 0.0)
    esv = volume_info.get("esv", 0.0)
    tumor_volume = volume_info.get("tumor_volume")
    
    metrics_data = [
        ["Metric", "Value"],
        ["Ejection Fraction (EF)", f"{ef:.1f}%"],
        ["End Diastolic Volume (EDV)", f"{edv:.1f} ml"],
        ["End Systolic Volume (ESV)", f"{esv:.1f} ml"],
    ]
    
    if tumor_volume is not None:
        metrics_data.append(["Tumor Volume", f"{tumor_volume:.1f} ml"])
    
    metrics_table = Table(metrics_data, colWidths=[6*cm, 4*cm])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.5*cm))
    
    # ED/ES 프레임 이미지
    frames = analysis_result.get("frames", [])
    lv_masks = analysis_result.get("lv_masks", {})
    ed_idx = analysis_result.get("ed_frame_idx", 0)
    es_idx = analysis_result.get("es_frame_idx", 0)
    
    if frames and lv_masks:
        story.append(Paragraph("<b>Key Frames</b>", styles['Heading2']))
        story.append(Spacer(1, 0.3*cm))
        
        # ED 프레임 이미지 생성
        if ed_idx < len(frames):
            ed_img_path = _create_frame_image(frames[ed_idx], lv_masks.get("ed"), "ED")
            story.append(Image(str(ed_img_path), width=8*cm, height=8*cm))
            story.append(Spacer(1, 0.3*cm))
        
        # ES 프레임 이미지 생성
        if es_idx < len(frames):
            es_img_path = _create_frame_image(frames[es_idx], lv_masks.get("es"), "ES")
            story.append(Image(str(es_img_path), width=8*cm, height=8*cm))
            story.append(Spacer(1, 0.3*cm))
    
    # 메타데이터
    metadata = analysis_result.get("metadata", {})
    story.append(Paragraph("<b>Analysis Metadata</b>", styles['Heading2']))
    story.append(Spacer(1, 0.3*cm))
    
    meta_text = f"""
    <b>File:</b> {metadata.get('file_path', 'N/A')}<br/>
    <b>Number of Frames:</b> {metadata.get('num_frames', 'N/A')}<br/>
    <b>Frame Size:</b> {metadata.get('frame_size', 'N/A')}<br/>
    <b>FPS:</b> {analysis_result.get('fps', 'N/A'):.1f}
    """
    story.append(Paragraph(meta_text, styles['Normal']))
    
    # 푸터
    story.append(Spacer(1, 1*cm))
    footer = Paragraph(
        "<i>This report is generated for research purposes only. Not for diagnostic use.</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    )
    story.append(footer)
    
    # PDF 빌드
    doc.build(story)
    
    # 임시 이미지 파일 정리
    _cleanup_temp_images()


def _create_frame_image(frame: np.ndarray, mask: Optional[np.ndarray], label: str) -> Path:
    """프레임 이미지를 임시 파일로 저장"""
    from utils.spec import PROJECT_ROOT
    temp_dir = PROJECT_ROOT / "temp_images"
    temp_dir.mkdir(exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(8, 8))
    
    # 프레임 표시
    if len(frame.shape) == 3:
        ax.imshow(frame, cmap='gray')
    else:
        ax.imshow(frame, cmap='gray')
    
    # 마스크 오버레이
    if mask is not None:
        ax.contour(mask, levels=[0.5], colors=['red'], linewidths=2)
    
    ax.set_title(f"{label} Frame", fontsize=16)
    ax.axis('off')
    
    # 이미지 저장
    img_path = temp_dir / f"{label}_frame.png"
    fig.savefig(str(img_path), bbox_inches='tight', dpi=100)
    plt.close(fig)
    
    return img_path


def _cleanup_temp_images():
    """임시 이미지 파일 정리"""
    from utils.spec import PROJECT_ROOT
    temp_dir = PROJECT_ROOT / "temp_images"
    if temp_dir.exists():
        for img_file in temp_dir.glob("*.png"):
            try:
                img_file.unlink()
            except:
                pass

