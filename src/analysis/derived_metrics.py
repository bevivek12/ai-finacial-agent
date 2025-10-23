"""Derived Metrics Computer for calculating financial ratios and metrics."""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

from ..models.schemas import FinancialMetric, EntityType, ExtractionMethod
from ..utils.config import get_config
from ..utils.logger import get_logger

logger = get_logger({"module": "derived_metrics"})


class DerivedMetricsComputer:
    """Service for computing derived financial metrics and ratios."""
    
    def __init__(self):
        """Initialize the derived metrics computer."""
        self.config = get_config()
        self.logger = logger
    
    def compute_all_metrics(
        self,
        validated_metrics: List[FinancialMetric]
    ) -> List[FinancialMetric]:
        """
        Compute all possible derived metrics from validated base metrics.
        
        Args:
            validated_metrics: List of validated base metrics
            
        Returns:
            List of derived metrics
        """
        self.logger.info("computing_derived_metrics", base_metrics=len(validated_metrics))
        
        # Create a lookup dictionary for easy access
        metrics_dict = self._create_metrics_dict(validated_metrics)
        
        derived_metrics = []
        
        # Growth rates
        derived_metrics.extend(self._compute_growth_rates(metrics_dict))
        
        # Profitability ratios
        derived_metrics.extend(self._compute_profitability_ratios(metrics_dict))
        
        # Leverage ratios
        derived_metrics.extend(self._compute_leverage_ratios(metrics_dict))
        
        # Liquidity ratios
        derived_metrics.extend(self._compute_liquidity_ratios(metrics_dict))
        
        self.logger.info("derived_metrics_computed", count=len(derived_metrics))
        
        return derived_metrics
    
    def _create_metrics_dict(
        self,
        metrics: List[FinancialMetric]
    ) -> Dict[str, Dict[str, FinancialMetric]]:
        """
        Create a dictionary for easy metric lookup by name and period.
        
        Args:
            metrics: List of financial metrics
            
        Returns:
            Dictionary: {metric_name: {period: metric}}
        """
        metrics_dict = {}
        
        for metric in metrics:
            name = metric.metric_name.lower().replace(' ', '_')
            period = str(metric.period_end_date.year)
            
            if name not in metrics_dict:
                metrics_dict[name] = {}
            
            metrics_dict[name][period] = metric
        
        return metrics_dict
    
    def _compute_growth_rates(
        self,
        metrics_dict: Dict[str, Dict[str, FinancialMetric]]
    ) -> List[FinancialMetric]:
        """
        Compute year-over-year growth rates.
        
        Args:
            metrics_dict: Dictionary of metrics by name and period
            
        Returns:
            List of growth rate metrics
        """
        growth_metrics = []
        
        # Metrics to calculate growth for
        growth_targets = [
            ('revenue', 'Revenue Growth'),
            ('ebitda', 'EBITDA Growth'),
            ('net_income', 'Net Income Growth'),
            ('operating_profit', 'Operating Profit Growth')
        ]
        
        for metric_key, metric_name in growth_targets:
            if metric_key not in metrics_dict:
                continue
            
            periods = sorted(metrics_dict[metric_key].keys())
            
            for i in range(1, len(periods)):
                current_period = periods[i]
                prior_period = periods[i-1]
                
                current_metric = metrics_dict[metric_key][current_period]
                prior_metric = metrics_dict[metric_key][prior_period]
                
                try:
                    # Calculate YoY growth rate
                    growth_rate = self._calculate_growth_rate(
                        current_metric.value,
                        prior_metric.value
                    )
                    
                    if growth_rate is not None:
                        growth_metric = FinancialMetric(
                            metric_id=f"{metric_key}_growth_{current_period}",
                            metric_name=f"{metric_name} YoY",
                            value=growth_rate,
                            currency="",  # Growth rates are unitless
                            scale="actual",  # Percentage
                            period_end_date=current_metric.period_end_date,
                            entity_type=current_metric.entity_type,
                            extraction_method=ExtractionMethod.CALCULATED,
                            notes=f"Calculated from {prior_period} to {current_period}"
                        )
                        
                        growth_metrics.append(growth_metric)
                        
                        self.logger.debug(
                            "growth_rate_calculated",
                            metric=metric_name,
                            period=current_period,
                            growth_rate=float(growth_rate)
                        )
                
                except Exception as e:
                    self.logger.warning(
                        "growth_rate_calculation_failed",
                        metric=metric_key,
                        error=str(e)
                    )
        
        return growth_metrics
    
    def _compute_profitability_ratios(
        self,
        metrics_dict: Dict[str, Dict[str, FinancialMetric]]
    ) -> List[FinancialMetric]:
        """
        Compute profitability ratios (margins).
        
        Args:
            metrics_dict: Dictionary of metrics
            
        Returns:
            List of profitability ratio metrics
        """
        ratio_metrics = []
        
        # Get all periods
        all_periods = set()
        for metric_periods in metrics_dict.values():
            all_periods.update(metric_periods.keys())
        
        for period in all_periods:
            # EBITDA Margin = EBITDA / Revenue
            if 'ebitda' in metrics_dict and 'revenue' in metrics_dict:
                if period in metrics_dict['ebitda'] and period in metrics_dict['revenue']:
                    ebitda = metrics_dict['ebitda'][period]
                    revenue = metrics_dict['revenue'][period]
                    
                    margin = self._calculate_ratio(ebitda.value, revenue.value)
                    if margin is not None:
                        ratio_metrics.append(
                            self._create_ratio_metric(
                                f"ebitda_margin_{period}",
                                "EBITDA Margin",
                                margin,
                                ebitda.period_end_date,
                                ebitda.entity_type,
                                "EBITDA / Revenue"
                            )
                        )
            
            # Net Margin = Net Income / Revenue
            if 'net_income' in metrics_dict and 'revenue' in metrics_dict:
                if period in metrics_dict['net_income'] and period in metrics_dict['revenue']:
                    net_income = metrics_dict['net_income'][period]
                    revenue = metrics_dict['revenue'][period]
                    
                    margin = self._calculate_ratio(net_income.value, revenue.value)
                    if margin is not None:
                        ratio_metrics.append(
                            self._create_ratio_metric(
                                f"net_margin_{period}",
                                "Net Margin",
                                margin,
                                net_income.period_end_date,
                                net_income.entity_type,
                                "Net Income / Revenue"
                            )
                        )
            
            # Operating Margin = Operating Profit / Revenue
            if 'operating_profit' in metrics_dict and 'revenue' in metrics_dict:
                if period in metrics_dict['operating_profit'] and period in metrics_dict['revenue']:
                    op_profit = metrics_dict['operating_profit'][period]
                    revenue = metrics_dict['revenue'][period]
                    
                    margin = self._calculate_ratio(op_profit.value, revenue.value)
                    if margin is not None:
                        ratio_metrics.append(
                            self._create_ratio_metric(
                                f"operating_margin_{period}",
                                "Operating Margin",
                                margin,
                                op_profit.period_end_date,
                                op_profit.entity_type,
                                "Operating Profit / Revenue"
                            )
                        )
        
        return ratio_metrics
    
    def _compute_leverage_ratios(
        self,
        metrics_dict: Dict[str, Dict[str, FinancialMetric]]
    ) -> List[FinancialMetric]:
        """
        Compute leverage ratios.
        
        Args:
            metrics_dict: Dictionary of metrics
            
        Returns:
            List of leverage ratio metrics
        """
        ratio_metrics = []
        
        all_periods = set()
        for metric_periods in metrics_dict.values():
            all_periods.update(metric_periods.keys())
        
        for period in all_periods:
            # Net Debt / EBITDA
            net_debt_key = None
            for key in ['net_debt', 'total_debt']:
                if key in metrics_dict and period in metrics_dict[key]:
                    net_debt_key = key
                    break
            
            if net_debt_key and 'ebitda' in metrics_dict:
                if period in metrics_dict['ebitda']:
                    debt = metrics_dict[net_debt_key][period]
                    ebitda = metrics_dict['ebitda'][period]
                    
                    ratio = self._calculate_ratio(debt.value, ebitda.value, as_percentage=False)
                    if ratio is not None:
                        ratio_metrics.append(
                            self._create_ratio_metric(
                                f"debt_to_ebitda_{period}",
                                "Net Debt / EBITDA",
                                ratio,
                                debt.period_end_date,
                                debt.entity_type,
                                f"{net_debt_key.replace('_', ' ').title()} / EBITDA",
                                as_percentage=False
                            )
                        )
            
            # Debt-to-Equity
            if 'total_debt' in metrics_dict and 'total_equity' in metrics_dict:
                if period in metrics_dict['total_debt'] and period in metrics_dict['total_equity']:
                    debt = metrics_dict['total_debt'][period]
                    equity = metrics_dict['total_equity'][period]
                    
                    ratio = self._calculate_ratio(debt.value, equity.value, as_percentage=False)
                    if ratio is not None:
                        ratio_metrics.append(
                            self._create_ratio_metric(
                                f"debt_to_equity_{period}",
                                "Debt-to-Equity",
                                ratio,
                                debt.period_end_date,
                                debt.entity_type,
                                "Total Debt / Total Equity",
                                as_percentage=False
                            )
                        )
        
        return ratio_metrics
    
    def _compute_liquidity_ratios(
        self,
        metrics_dict: Dict[str, Dict[str, FinancialMetric]]
    ) -> List[FinancialMetric]:
        """
        Compute liquidity ratios.
        
        Args:
            metrics_dict: Dictionary of metrics
            
        Returns:
            List of liquidity ratio metrics
        """
        ratio_metrics = []
        
        all_periods = set()
        for metric_periods in metrics_dict.values():
            all_periods.update(metric_periods.keys())
        
        for period in all_periods:
            # Current Ratio = Current Assets / Current Liabilities
            if 'current_assets' in metrics_dict and 'current_liabilities' in metrics_dict:
                if period in metrics_dict['current_assets'] and period in metrics_dict['current_liabilities']:
                    assets = metrics_dict['current_assets'][period]
                    liabilities = metrics_dict['current_liabilities'][period]
                    
                    ratio = self._calculate_ratio(assets.value, liabilities.value, as_percentage=False)
                    if ratio is not None:
                        ratio_metrics.append(
                            self._create_ratio_metric(
                                f"current_ratio_{period}",
                                "Current Ratio",
                                ratio,
                                assets.period_end_date,
                                assets.entity_type,
                                "Current Assets / Current Liabilities",
                                as_percentage=False
                            )
                        )
            
            # Cash Ratio = Cash / Current Liabilities
            cash_key = None
            for key in ['cash', 'cash_and_equivalents', 'cash_and_cash_equivalents']:
                if key in metrics_dict and period in metrics_dict[key]:
                    cash_key = key
                    break
            
            if cash_key and 'current_liabilities' in metrics_dict:
                if period in metrics_dict['current_liabilities']:
                    cash = metrics_dict[cash_key][period]
                    liabilities = metrics_dict['current_liabilities'][period]
                    
                    ratio = self._calculate_ratio(cash.value, liabilities.value, as_percentage=False)
                    if ratio is not None:
                        ratio_metrics.append(
                            self._create_ratio_metric(
                                f"cash_ratio_{period}",
                                "Cash Ratio",
                                ratio,
                                cash.period_end_date,
                                cash.entity_type,
                                "Cash / Current Liabilities",
                                as_percentage=False
                            )
                        )
        
        return ratio_metrics
    
    def _calculate_growth_rate(
        self,
        current_value: Decimal,
        prior_value: Decimal
    ) -> Optional[Decimal]:
        """
        Calculate year-over-year growth rate as a percentage.
        
        Args:
            current_value: Current period value
            prior_value: Prior period value
            
        Returns:
            Growth rate as decimal (e.g., 0.15 for 15%) or None if invalid
        """
        try:
            if prior_value == 0:
                return None
            
            growth_rate = (current_value - prior_value) / abs(prior_value)
            
            # Validate growth rate is reasonable
            if growth_rate > self.config.validation.yoy_growth_max or \
               growth_rate < self.config.validation.yoy_growth_min:
                self.logger.warning(
                    "growth_rate_out_of_bounds",
                    growth_rate=float(growth_rate),
                    max=self.config.validation.yoy_growth_max,
                    min=self.config.validation.yoy_growth_min
                )
            
            return growth_rate
            
        except (InvalidOperation, ZeroDivisionError, TypeError):
            return None
    
    def _calculate_ratio(
        self,
        numerator: Decimal,
        denominator: Decimal,
        as_percentage: bool = True
    ) -> Optional[Decimal]:
        """
        Calculate a ratio.
        
        Args:
            numerator: Numerator value
            denominator: Denominator value
            as_percentage: If True, return as percentage (multiply by 100)
            
        Returns:
            Ratio value or None if invalid
        """
        try:
            if denominator == 0:
                return None
            
            ratio = numerator / denominator
            
            if as_percentage:
                # Return as percentage but don't multiply (0.15 = 15%)
                # Validate margin is reasonable
                if ratio > self.config.validation.margin_max or \
                   ratio < self.config.validation.margin_min:
                    self.logger.warning(
                        "ratio_out_of_bounds",
                        ratio=float(ratio)
                    )
            
            return ratio
            
        except (InvalidOperation, ZeroDivisionError, TypeError):
            return None
    
    def _create_ratio_metric(
        self,
        metric_id: str,
        metric_name: str,
        value: Decimal,
        period_end_date: date,
        entity_type: EntityType,
        formula: str,
        as_percentage: bool = True
    ) -> FinancialMetric:
        """
        Create a FinancialMetric for a calculated ratio.
        
        Args:
            metric_id: Metric ID
            metric_name: Display name
            value: Calculated value
            period_end_date: Period date
            entity_type: Entity type
            formula: Formula used
            as_percentage: Whether value is a percentage
            
        Returns:
            FinancialMetric object
        """
        return FinancialMetric(
            metric_id=metric_id,
            metric_name=metric_name,
            value=value,
            currency="" if as_percentage else "ratio",
            scale="actual",
            period_end_date=period_end_date,
            entity_type=entity_type,
            extraction_method=ExtractionMethod.CALCULATED,
            notes=f"Formula: {formula}"
        )
