"""
Financial Commentary Generator.

This service generates narrative financial commentary using LLM:
1. Analyze validated metrics and trends
2. Generate insights on performance
3. Create executive summary
4. Highlight key financial ratios and changes
"""

from typing import List, Dict, Optional
from decimal import Decimal
from datetime import date
from loguru import logger

from src.models.schemas import FinancialMetric, EntityType


class FinancialCommentaryGenerator:
    """
    Generate narrative financial commentary from validated metrics.
    
    Generates:
    - Executive summary
    - Revenue analysis
    - Profitability analysis
    - Balance sheet analysis
    - Cash flow analysis
    - Key ratio commentary
    """
    
    EXECUTIVE_SUMMARY_PROMPT = """You are a financial analyst writing an executive summary for a company's financial performance.

**Financial Metrics:**
{metrics_summary}

**Year-over-Year Changes:**
{yoy_changes}

**Key Ratios:**
{key_ratios}

**Task:**
Write a concise executive summary (3-4 paragraphs) covering:
1. Overall financial performance
2. Revenue trends and drivers
3. Profitability and margin analysis
4. Balance sheet strength
5. Key highlights and concerns

Use professional financial language. Be objective and data-driven."""
    
    SECTION_COMMENTARY_PROMPT = """You are a financial analyst writing detailed commentary for the {section_name} section.

**Metrics:**
{section_metrics}

**Trends:**
{trends}

**Task:**
Write detailed commentary (2-3 paragraphs) analyzing:
1. Current period performance
2. Historical trends
3. Key drivers and changes
4. Notable observations

Use professional financial language."""
    
    def __init__(self, llm_client=None, model: str = "gpt-4"):
        """
        Initialize commentary generator.
        
        Args:
            llm_client: LLM client instance
            model: Model name to use
        """
        self.llm_client = llm_client
        self.model = model
        self.logger = logger.bind(component="commentary_generator")
    
    def generate_full_commentary(
        self,
        metrics: List[FinancialMetric],
        derived_metrics: Optional[List[FinancialMetric]] = None
    ) -> Dict[str, str]:
        """
        Generate complete financial commentary.
        
        Args:
            metrics: Validated financial metrics
            derived_metrics: Derived metrics (ratios, growth rates)
        
        Returns:
            Dictionary with commentary sections
        """
        self.logger.info("generating_full_commentary", metrics=len(metrics))
        
        all_metrics = metrics + (derived_metrics or [])
        
        commentary = {
            "executive_summary": self.generate_executive_summary(all_metrics),
            "revenue_analysis": self.generate_section_commentary(all_metrics, "revenue"),
            "profitability_analysis": self.generate_section_commentary(all_metrics, "profitability"),
            "balance_sheet_analysis": self.generate_section_commentary(all_metrics, "balance_sheet"),
            "cash_flow_analysis": self.generate_section_commentary(all_metrics, "cash_flow"),
        }
        
        self.logger.info("commentary_generated", sections=len(commentary))
        
        return commentary
    
    def generate_executive_summary(self, metrics: List[FinancialMetric]) -> str:
        """Generate executive summary."""
        self.logger.info("generating_executive_summary")
        
        # Prepare metrics summary
        metrics_summary = self._format_metrics_summary(metrics)
        
        # Calculate YoY changes
        yoy_changes = self._calculate_yoy_changes(metrics)
        
        # Extract key ratios
        key_ratios = self._extract_key_ratios(metrics)
        
        # Build prompt
        prompt = self.EXECUTIVE_SUMMARY_PROMPT.format(
            metrics_summary=metrics_summary,
            yoy_changes=yoy_changes,
            key_ratios=key_ratios
        )
        
        # Query LLM
        if self.llm_client is None:
            return self._generate_fallback_summary(metrics)
        
        try:
            summary = self._query_llm(prompt)
            return summary
        except Exception as e:
            self.logger.error("executive_summary_generation_failed", error=str(e))
            return self._generate_fallback_summary(metrics)
    
    def generate_section_commentary(
        self,
        metrics: List[FinancialMetric],
        section: str
    ) -> str:
        """
        Generate commentary for a specific financial section.
        
        Args:
            metrics: All metrics
            section: Section name (revenue, profitability, balance_sheet, cash_flow)
        
        Returns:
            Section commentary text
        """
        self.logger.info("generating_section_commentary", section=section)
        
        # Filter metrics for this section
        section_metrics = self._filter_metrics_by_section(metrics, section)
        
        if not section_metrics:
            return f"No data available for {section} analysis."
        
        # Format section metrics
        metrics_formatted = self._format_section_metrics(section_metrics)
        
        # Calculate trends
        trends = self._calculate_trends(section_metrics)
        
        # Build prompt
        prompt = self.SECTION_COMMENTARY_PROMPT.format(
            section_name=section.replace("_", " ").title(),
            section_metrics=metrics_formatted,
            trends=trends
        )
        
        # Query LLM
        if self.llm_client is None:
            return self._generate_fallback_section_commentary(section, section_metrics)
        
        try:
            commentary = self._query_llm(prompt)
            return commentary
        except Exception as e:
            self.logger.error("section_commentary_failed", section=section, error=str(e))
            return self._generate_fallback_section_commentary(section, section_metrics)
    
    def _format_metrics_summary(self, metrics: List[FinancialMetric]) -> str:
        """Format metrics for summary prompt."""
        # Get latest period
        latest_period = max(m.period_end_date for m in metrics if m.period_end_date)
        
        # Filter latest metrics
        latest_metrics = [m for m in metrics if m.period_end_date == latest_period]
        
        # Group by category
        revenue_metrics = [m for m in latest_metrics if "revenue" in m.metric_name.lower()]
        profit_metrics = [m for m in latest_metrics if "profit" in m.metric_name.lower() or "income" in m.metric_name.lower()]
        asset_metrics = [m for m in latest_metrics if "asset" in m.metric_name.lower()]
        
        lines = [f"**Period:** {latest_period}\n"]
        
        if revenue_metrics:
            lines.append("**Revenue Metrics:**")
            for m in revenue_metrics:
                lines.append(f"- {m.metric_name}: {m.value} {m.currency} ({m.scale})")
        
        if profit_metrics:
            lines.append("\n**Profitability Metrics:**")
            for m in profit_metrics:
                lines.append(f"- {m.metric_name}: {m.value} {m.currency} ({m.scale})")
        
        if asset_metrics:
            lines.append("\n**Balance Sheet Metrics:**")
            for m in asset_metrics[:5]:  # Limit to top 5
                lines.append(f"- {m.metric_name}: {m.value} {m.currency} ({m.scale})")
        
        return "\n".join(lines)
    
    def _calculate_yoy_changes(self, metrics: List[FinancialMetric]) -> str:
        """Calculate and format YoY changes."""
        # Find metrics with prior year data
        yoy_lines = []
        
        # Group by metric name
        from collections import defaultdict
        by_metric = defaultdict(list)
        for m in metrics:
            by_metric[m.metric_name].append(m)
        
        for metric_name, metric_list in by_metric.items():
            if len(metric_list) < 2:
                continue
            
            # Sort by date
            sorted_metrics = sorted(metric_list, key=lambda x: x.period_end_date, reverse=True)
            
            # Calculate YoY for most recent
            current = sorted_metrics[0]
            prior = sorted_metrics[1]
            
            if prior.value != 0:
                yoy_change = ((current.value - prior.value) / abs(prior.value)) * 100
                yoy_lines.append(
                    f"- {metric_name}: {yoy_change:+.1f}% ({current.value} vs {prior.value})"
                )
        
        if not yoy_lines:
            return "No year-over-year comparison data available."
        
        return "\n".join(yoy_lines[:10])  # Limit to top 10
    
    def _extract_key_ratios(self, metrics: List[FinancialMetric]) -> str:
        """Extract and format key financial ratios."""
        # Look for ratio metrics
        ratio_metrics = [
            m for m in metrics
            if any(keyword in m.metric_name.lower() for keyword in [
                "ratio", "margin", "return", "yield", "coverage"
            ])
        ]
        
        if not ratio_metrics:
            return "No ratio metrics available."
        
        # Get latest period
        latest_period = max(m.period_end_date for m in ratio_metrics if m.period_end_date)
        latest_ratios = [m for m in ratio_metrics if m.period_end_date == latest_period]
        
        lines = []
        for m in latest_ratios[:8]:  # Limit to 8 ratios
            lines.append(f"- {m.metric_name}: {m.value}")
        
        return "\n".join(lines)
    
    def _filter_metrics_by_section(
        self,
        metrics: List[FinancialMetric],
        section: str
    ) -> List[FinancialMetric]:
        """Filter metrics by financial section."""
        section_keywords = {
            "revenue": ["revenue", "sales", "turnover"],
            "profitability": ["profit", "income", "ebitda", "margin", "earnings"],
            "balance_sheet": ["asset", "liability", "equity", "cash", "debt"],
            "cash_flow": ["cash flow", "operating cash", "free cash flow", "capex"],
        }
        
        keywords = section_keywords.get(section, [])
        
        filtered = [
            m for m in metrics
            if any(kw in m.metric_name.lower() for kw in keywords)
        ]
        
        return filtered
    
    def _format_section_metrics(self, metrics: List[FinancialMetric]) -> str:
        """Format metrics for section commentary."""
        if not metrics:
            return "No metrics available."
        
        # Get latest period
        latest_period = max(m.period_end_date for m in metrics if m.period_end_date)
        latest_metrics = [m for m in metrics if m.period_end_date == latest_period]
        
        lines = [f"**Period:** {latest_period}\n"]
        for m in latest_metrics[:10]:  # Limit to 10
            lines.append(f"- {m.metric_name}: {m.value} {m.currency} ({m.scale})")
        
        return "\n".join(lines)
    
    def _calculate_trends(self, metrics: List[FinancialMetric]) -> str:
        """Calculate trends for metrics."""
        # Group by metric name
        from collections import defaultdict
        by_metric = defaultdict(list)
        for m in metrics:
            by_metric[m.metric_name].append(m)
        
        trend_lines = []
        for metric_name, metric_list in by_metric.items():
            if len(metric_list) < 2:
                continue
            
            # Sort by date
            sorted_metrics = sorted(metric_list, key=lambda x: x.period_end_date)
            
            # Simple trend: increasing/decreasing
            values = [m.value for m in sorted_metrics]
            if values[-1] > values[0]:
                trend = "Increasing"
            elif values[-1] < values[0]:
                trend = "Decreasing"
            else:
                trend = "Stable"
            
            change = ((values[-1] - values[0]) / abs(values[0])) * 100 if values[0] != 0 else 0
            
            trend_lines.append(
                f"- {metric_name}: {trend} ({change:+.1f}% over {len(values)} periods)"
            )
        
        if not trend_lines:
            return "No trend data available."
        
        return "\n".join(trend_lines[:8])
    
    def _query_llm(self, prompt: str) -> str:
        """Query LLM for commentary generation."""
        try:
            if hasattr(self.llm_client, 'chat'):
                # OpenAI-style client
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a professional financial analyst."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=800
                )
                return response.choices[0].message.content
            else:
                # Generic client
                return self.llm_client.generate(prompt)
        except Exception as e:
            self.logger.error("llm_query_failed", error=str(e))
            raise
    
    def _generate_fallback_summary(self, metrics: List[FinancialMetric]) -> str:
        """Generate basic summary without LLM."""
        latest_period = max(m.period_end_date for m in metrics if m.period_end_date)
        latest_metrics = [m for m in metrics if m.period_end_date == latest_period]
        
        revenue = next((m for m in latest_metrics if "revenue" in m.metric_name.lower()), None)
        net_income = next((m for m in latest_metrics if "net_income" in m.metric_name.lower()), None)
        
        summary = f"**Executive Summary**\n\n"
        summary += f"For the period ending {latest_period}, "
        
        if revenue:
            summary += f"the company reported revenue of {revenue.value} {revenue.currency} ({revenue.scale}). "
        
        if net_income:
            summary += f"Net income was {net_income.value} {net_income.currency} ({net_income.scale}). "
        
        summary += f"\n\nThis analysis is based on {len(latest_metrics)} extracted metrics."
        
        return summary
    
    def _generate_fallback_section_commentary(
        self,
        section: str,
        metrics: List[FinancialMetric]
    ) -> str:
        """Generate basic section commentary without LLM."""
        if not metrics:
            return f"No data available for {section} analysis."
        
        latest_period = max(m.period_end_date for m in metrics if m.period_end_date)
        latest_metrics = [m for m in metrics if m.period_end_date == latest_period]
        
        commentary = f"**{section.replace('_', ' ').title()}**\n\n"
        commentary += f"For the period ending {latest_period}:\n\n"
        
        for m in latest_metrics[:5]:
            commentary += f"- {m.metric_name}: {m.value} {m.currency} ({m.scale})\n"
        
        return commentary
