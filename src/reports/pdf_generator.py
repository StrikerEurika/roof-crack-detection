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
            
            # Build visual evidence HTML block
            visual_evidence = ""
            if os.path.exists(original_path):
                visual_evidence += f"""
                <div class="image-box" style="margin-right: 2%;">
                    <img src="{original_path}">
                    <p>Original Roof Image</p>
                </div>
                """
            if vis_path and os.path.exists(vis_path):
                visual_evidence += f"""
                <div class="image-box">
                    <img src="{vis_path}">
                    <p>Analyzed Surface Overlay & Detections</p>
                </div>
                """

            # Load report template
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "report_template.html")
            with open(template_path, "r", encoding="utf-8") as f:
                html = f.read()

            # Format the template with record values
            html = html.replace("{status_color}", status_color)
            html = html.replace("{status_text}", status_text)
            html = html.replace("{inspection_id}", record.get("id", "N/A"))
            html = html.replace("{image_name}", record.get("image_name", "N/A"))
            html = html.replace("{formatted_date}", formatted_date)
            html = html.replace("{model_used}", record.get("model_used", "N/A"))
            html = html.replace("{confidence}", f"{record.get('confidence', 0.0) * 100:.1f}%")
            html = html.replace("{elapsed_time}", f"{record.get('elapsed_time', 0.0):.2f}")
            html = html.replace("{crack_count}", str(record.get("crack_count", 0)))
            html = html.replace("{severity}", severity)
            html = html.replace("{recommendation}", recommendation)
            html = html.replace("{visual_evidence}", visual_evidence)

            # Create QTextDocument and print to QPrinter
            doc = QTextDocument()
            doc.setHtml(html)
            
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(output_pdf_path)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            printer.setPageMargins(0.5, 0.5, 0.5, 0.5, QPrinter.Unit.Inch)
            
            # Execute print
            doc.print_(printer)
            return True
            
        except Exception as e:
            print(f"Error generating PDF report: {e}")
            return False
