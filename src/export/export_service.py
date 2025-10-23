"""
Export Service.

This service orchestrates the export of financial data to multiple formats:
1. Word documents
2. Excel workbooks
3. JSON files (optional)
"""

from typing import List, Dict, Optional
from datetime import date
from pathlib import Path
import json
from loguru import logger

from src.models.schemas import FinancialMetric
from src.export.word_template import WordTemplateGenerator
from src.export.excel_template import ExcelTemplateGenerator


class ExportService:
    """
    Service for exporting financial data to various formats.
    
    Supports:
    - Word documents (.docx)
    - Excel workbooks (.xlsx)
    - JSON files (.json)
    """
    
    def __init__(self, output_dir: str = "./output"):
        """
        Initialize export service.
        
        Args:
            output_dir: Base output directory for exports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.word_generator = WordTemplateGenerator()
        self.excel_generator = ExcelTemplateGenerator()
        
        self.logger = logger.bind(component="export_service")
    
    def export_all(
        self,
        company_name: str,
        report_period: date,
        metrics: List[FinancialMetric],
        derived_metrics: Optional[List[FinancialMetric]] = None,
        commentary: Optional[Dict[str, str]] = None,
        formats: List[str] = ["word", "excel", "json"]
    ) -> Dict[str, str]:
        """
        Export financial data to all requested formats.
        
        Args:
            company_name: Company name
            report_period: Reporting period
            metrics: Financial metrics
            derived_metrics: Derived metrics (ratios, etc.)
            commentary: Commentary sections
            formats: List of export formats (word, excel, json)
        
        Returns:
            Dictionary mapping format to output file path
        """
        self.logger.info(
            "exporting_financial_data",
            company=company_name,
            formats=formats
        )
        
        exported_files = {}
        
        # Create safe filename base
        safe_company = company_name.replace(" ", "_").replace("/", "_")
        period_str = report_period.strftime("%Y%m%d")
        base_filename = f"{safe_company}_{period_str}"
        
        # Export to Word
        if "word" in formats:
            try:
                word_path = self.export_to_word(
                    company_name=company_name,
                    report_period=report_period,
                    metrics=metrics,
                    commentary=commentary or {},
                    filename=f"{base_filename}.docx"
                )
                exported_files["word"] = word_path
            except Exception as e:
                self.logger.error("word_export_failed", error=str(e))
        
        # Export to Excel
        if "excel" in formats:
            try:
                excel_path = self.export_to_excel(
                    company_name=company_name,
                    report_period=report_period,
                    metrics=metrics,
                    derived_metrics=derived_metrics,
                    filename=f"{base_filename}.xlsx"
                )
                exported_files["excel"] = excel_path
            except Exception as e:
                self.logger.error("excel_export_failed", error=str(e))
        
        # Export to JSON
        if "json" in formats:
            try:
                json_path = self.export_to_json(
                    company_name=company_name,
                    report_period=report_period,
                    metrics=metrics,
                    derived_metrics=derived_metrics,
                    commentary=commentary,
                    filename=f"{base_filename}.json"
                )
                exported_files["json"] = json_path
            except Exception as e:
                self.logger.error("json_export_failed", error=str(e))
        
        self.logger.info(
            "export_complete",
            formats_exported=len(exported_files),
            files=list(exported_files.values())
        )
        
        return exported_files
    
    def export_to_word(
        self,
        company_name: str,
        report_period: date,
        metrics: List[FinancialMetric],
        commentary: Dict[str, str],
        filename: Optional[str] = None
    ) -> str:
        """
        Export to Word document.
        
        Args:
            company_name: Company name
            report_period: Reporting period
            metrics: Financial metrics
            commentary: Commentary sections
            filename: Output filename (optional)
        
        Returns:
            Path to generated Word document
        """
        if filename is None:
            filename = f"financial_report_{report_period.strftime('%Y%m%d')}.docx"
        
        output_path = self.output_dir / filename
        
        self.logger.info("exporting_to_word", path=str(output_path))
        
        word_path = self.word_generator.create_financial_report(
            company_name=company_name,
            report_period=report_period,
            metrics=metrics,
            commentary=commentary,
            output_path=str(output_path)
        )
        
        return word_path
    
    def export_to_excel(
        self,
        company_name: str,
        report_period: date,
        metrics: List[FinancialMetric],
        derived_metrics: Optional[List[FinancialMetric]] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Export to Excel workbook.
        
        Args:
            company_name: Company name
            report_period: Reporting period
            metrics: Financial metrics
            derived_metrics: Derived metrics
            filename: Output filename (optional)
        
        Returns:
            Path to generated Excel workbook
        """
        if filename is None:
            filename = f"financial_report_{report_period.strftime('%Y%m%d')}.xlsx"
        
        output_path = self.output_dir / filename
        
        self.logger.info("exporting_to_excel", path=str(output_path))
        
        excel_path = self.excel_generator.create_financial_workbook(
            company_name=company_name,
            report_period=report_period,
            metrics=metrics,
            derived_metrics=derived_metrics,
            output_path=str(output_path)
        )
        
        return excel_path
    
    def export_to_json(
        self,
        company_name: str,
        report_period: date,
        metrics: List[FinancialMetric],
        derived_metrics: Optional[List[FinancialMetric]] = None,
        commentary: Optional[Dict[str, str]] = None,
        filename: Optional[str] = None
    ) -> str:
        """
        Export to JSON file.
        
        Args:
            company_name: Company name
            report_period: Reporting period
            metrics: Financial metrics
            derived_metrics: Derived metrics
            commentary: Commentary sections
            filename: Output filename (optional)
        
        Returns:
            Path to generated JSON file
        """
        if filename is None:
            filename = f"financial_data_{report_period.strftime('%Y%m%d')}.json"
        
        output_path = self.output_dir / filename
        
        self.logger.info("exporting_to_json", path=str(output_path))
        
        # Prepare data structure
        data = {
            "company_name": company_name,
            "report_period": report_period.strftime("%Y-%m-%d"),
            "metrics": [self._metric_to_dict(m) for m in metrics],
        }
        
        if derived_metrics:
            data["derived_metrics"] = [self._metric_to_dict(m) for m in derived_metrics]
        
        if commentary:
            data["commentary"] = commentary
        
        # Write JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(output_path)
    
    def _metric_to_dict(self, metric: FinancialMetric) -> Dict:
        """Convert FinancialMetric to dictionary for JSON serialization."""
        return {
            "metric_id": metric.metric_id,
            "metric_name": metric.metric_name,
            "value": float(metric.value),
            "currency": metric.currency,
            "scale": metric.scale,
            "period_end_date": metric.period_end_date.strftime("%Y-%m-%d") if metric.period_end_date else None,
            "entity_type": metric.entity_type.value if metric.entity_type else None,
        }
    
    def create_summary_report(
        self,
        company_name: str,
        report_period: date,
        metrics: List[FinancialMetric],
        output_format: str = "txt"
    ) -> str:
        """
        Create a simple text summary report.
        
        Args:
            company_name: Company name
            report_period: Reporting period
            metrics: Financial metrics
            output_format: Output format (txt or md)
        
        Returns:
            Path to summary report
        """
        extension = "txt" if output_format == "txt" else "md"
        filename = f"summary_{report_period.strftime('%Y%m%d')}.{extension}"
        output_path = self.output_dir / filename
        
        # Get latest period metrics
        latest_metrics = [m for m in metrics if m.period_end_date == report_period]
        
        # Create summary text
        lines = []
        
        if output_format == "md":
            lines.append(f"# {company_name}")
            lines.append(f"## Financial Summary")
            lines.append(f"**Period Ending:** {report_period.strftime('%B %d, %Y')}")
            lines.append("")
            lines.append("### Key Metrics")
            lines.append("")
        else:
            lines.append(f"{company_name}")
            lines.append("=" * len(company_name))
            lines.append(f"Period Ending: {report_period.strftime('%B %d, %Y')}")
            lines.append("")
            lines.append("Key Metrics:")
            lines.append("-" * 40)
        
        # Add metrics
        for metric in latest_metrics[:10]:  # Top 10 metrics
            if output_format == "md":
                lines.append(f"- **{metric.metric_name}:** {metric.value:,.2f} {metric.currency} ({metric.scale})")
            else:
                lines.append(f"{metric.metric_name}: {metric.value:,.2f} {metric.currency} ({metric.scale})")
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
        self.logger.info("summary_report_created", path=str(output_path))
        
        return str(output_path)
