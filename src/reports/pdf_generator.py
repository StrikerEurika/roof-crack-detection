import os
from datetime import datetime
from PySide6.QtGui import QTextDocument, QPageSize
from PySide6.QtPrintSupport import QPrinter

class PDFReportGenerator:
    """Generates professional roof crack inspection reports in PDF format using Qt's native HTML printing."""

    @staticmethod
    def generate_report(record: dict, output_pdf_path: str) -> bool:
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
            
            # Format timestamp
            timestamp_str = record.get("timestamp", "")
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str)
                formatted_date = dt.strftime("%B %d, %Y - %I:%M %p")
            else:
                formatted_date = datetime.now().strftime("%B %d, %Y - %I:%M %p")

            # Determine status badge and recommendation
            crack_detected = record.get("crack_detected", False)
            if crack_detected:
                status_color = "#f43f5e"  # Coral Red
                status_text = "CRACK DETECTED (ACTION REQUIRED)"
                crack_count = record.get("crack_count", 0)
                if crack_count > 5:
                    severity = "HIGH"
                    recommendation = "<strong>CRITICAL SEVERITY:</strong> Multiple major cracks detected on the roof surface. Immediate structural intervention and repairs are strongly recommended to prevent water ingress and structural damage."
                elif crack_count > 2:
                    severity = "MEDIUM"
                    recommendation = "<strong>MODERATE SEVERITY:</strong> Several cracks detected. Recommend scheduling a physical inspection by a maintenance crew within the next 14 days to assess the crack depth and progression."
                else:
                    severity = "LOW"
                    recommendation = "<strong>LOW SEVERITY:</strong> Minor crack detected. Schedule routine monitoring and seal the crack during the next scheduled preventative maintenance cycle."
            else:
                status_color = "#10b981"  # Emerald Green
                status_text = "ROOF CLEAR (NO CRACKS DETECTED)"
                severity = "NONE"
                recommendation = "<strong>NO ACTION REQUIRED:</strong> The inspection did not identify any visible roof surface cracks. Recommend continuing with standard annual inspection intervals."

            # Image paths (with forward slashes for HTML rendering)
            original_path = record.get("image_path", "").replace("\\", "/")
            vis_path = record.get("vis_image_path", "").replace("\\", "/")
            
            # Build HTML content
            html = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Segoe UI', Arial, sans-serif;
                        color: #1e293b;
                        margin: 0;
                        padding: 0;
                    }}
                    .header {{
                        background-color: #121824;
                        color: #ffffff;
                        padding: 20px;
                        border-bottom: 4px solid {status_color};
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 24px;
                        letter-spacing: 0.5px;
                    }}
                    .header p {{
                        margin: 5px 0 0 0;
                        color: #94a3b8;
                        font-size: 14px;
                    }}
                    .container {{
                        padding: 25px;
                    }}
                    .badge {{
                        background-color: {status_color};
                        color: white;
                        padding: 8px 15px;
                        border-radius: 4px;
                        font-weight: bold;
                        display: inline-block;
                        font-size: 14px;
                        margin-bottom: 20px;
                    }}
                    .section-title {{
                        font-size: 16px;
                        color: #0f172a;
                        border-bottom: 2px solid #e2e8f0;
                        padding-bottom: 5px;
                        margin-top: 25px;
                        margin-bottom: 15px;
                        font-weight: bold;
                    }}
                    .grid {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-bottom: 20px;
                    }}
                    .grid td {{
                        padding: 10px;
                        border: 1px solid #e2e8f0;
                        font-size: 13px;
                    }}
                    .grid td.label {{
                        background-color: #f8fafc;
                        font-weight: bold;
                        width: 25%;
                        color: #475569;
                    }}
                    .grid td.value {{
                        width: 25%;
                    }}
                    .kpi-container {{
                        margin-bottom: 20px;
                    }}
                    .kpi-card {{
                        background-color: #f8fafc;
                        border: 1px solid #e2e8f0;
                        border-radius: 6px;
                        padding: 15px;
                        text-align: center;
                        margin-right: 15px;
                    }}
                    .kpi-value {{
                        font-size: 22px;
                        font-weight: bold;
                        color: #0f172a;
                        margin-top: 5px;
                    }}
                    .kpi-label {{
                        font-size: 11px;
                        color: #64748b;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}
                    .recommendation-box {{
                        background-color: #f8fafc;
                        border-left: 5px solid {status_color};
                        padding: 15px;
                        font-size: 13px;
                        line-height: 1.5;
                        margin-bottom: 25px;
                        border-top: 1px solid #e2e8f0;
                        border-right: 1px solid #e2e8f0;
                        border-bottom: 1px solid #e2e8f0;
                        border-radius: 0 4px 4px 0;
                    }}
                    .image-container {{
                        text-align: center;
                        margin-top: 15px;
                    }}
                    .image-box {{
                        display: inline-block;
                        width: 48%;
                        vertical-align: top;
                    }}
                    .image-box img {{
                        width: 100%;
                        height: auto;
                        border: 2px solid #cbd5e1;
                        border-radius: 4px;
                        max-height: 320px;
                    }}
                    .image-box p {{
                        font-size: 12px;
                        color: #64748b;
                        margin-top: 5px;
                    }}
                    .footer {{
                        margin-top: 40px;
                        border-top: 1px solid #e2e8f0;
                        padding-top: 15px;
                        text-align: center;
                        font-size: 11px;
                        color: #94a3b8;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>ROOF CRACK DETECTION REPORT</h1>
                    <p>Roof Inspection ID: {record.get("id", "N/A")}</p>
                </div>
                
                <div class="container">
                    <div class="badge">{status_text}</div>
                    
                    <div class="section-title">Inspection Summary</div>
                    <table class="grid">
                        <tr>
                            <td class="label">Image Name</td>
                            <td class="value" colspan="3">{record.get("image_name", "N/A")}</td>
                        </tr>
                        <tr>
                            <td class="label">Date & Time</td>
                            <td class="value">{formatted_date}</td>
                            <td class="label">Model Variant</td>
                            <td class="value">{record.get("model_used", "N/A")}</td>
                        </tr>
                        <tr>
                            <td class="label">Detection Confidence</td>
                            <td class="value">{record.get("confidence", 0.0) * 100:.1f}%</td>
                            <td class="label">Processing Duration</td>
                            <td class="value">{record.get("elapsed_time", 0.0):.2f} seconds</td>
                        </tr>
                        <tr>
                            <td class="label">Crack Regions Found</td>
                            <td class="value">{record.get("crack_count", 0)}</td>
                            <td class="label">Severity Rating</td>
                            <td class="value" style="font-weight: bold; color: {status_color};">{severity}</td>
                        </tr>
                    </table>
                    
                    <div class="section-title">Action & Recommendations</div>
                    <div class="recommendation-box">
                        {recommendation}
                    </div>
                    
                    <div class="section-title">Visual Evidence</div>
                    <div class="image-container">
            """
            
            # Embed image tags if files exist
            if os.path.exists(original_path):
                html += f"""
                        <div class="image-box" style="margin-right: 2%;">
                            <img src="{original_path}">
                            <p>Original Roof Image</p>
                        </div>
                """
            
            if vis_path and os.path.exists(vis_path):
                html += f"""
                        <div class="image-box">
                            <img src="{vis_path}">
                            <p>Analyzed Surface Overlay & Detections</p>
                        </div>
                """
                
            html += f"""
                    </div>
                    
                    <div class="footer">
                        Generated automatically by Roof Crack Inspection System Desktop Suite | Confident Material Analytics
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create QTextDocument and print to QPrinter
            doc = QTextDocument()
            doc.setHtml(html)
            
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(output_pdf_path)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            
            # Margins
            printer.setPageMargins(0.5, 0.5, 0.5, 0.5, QPrinter.Unit.Inch)
            
            # Execute print
            doc.print_(printer)
            return True
            
        except Exception as e:
            print(f"Error generating PDF report: {e}")
            return False
