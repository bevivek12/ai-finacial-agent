"""Currency conversion and scale adjustment utilities."""

from decimal import Decimal
from typing import Dict, Optional

from ..utils.logger import get_logger

logger = get_logger({"module": "currency_utils"})


class CurrencyConverter:
    """Utility for currency conversion."""
    
    # Static exchange rates (in production, would use live API)
    EXCHANGE_RATES = {
        # Base: GBP
        ("GBP", "USD"): Decimal("1.27"),
        ("GBP", "EUR"): Decimal("1.17"),
        ("USD", "GBP"): Decimal("0.79"),
        ("USD", "EUR"): Decimal("0.92"),
        ("EUR", "GBP"): Decimal("0.85"),
        ("EUR", "USD"): Decimal("1.09"),
        # Same currency
        ("GBP", "GBP"): Decimal("1.0"),
        ("USD", "USD"): Decimal("1.0"),
        ("EUR", "EUR"): Decimal("1.0"),
    }
    
    @classmethod
    def convert(
        cls,
        amount: Decimal,
        from_currency: str,
        to_currency: str
    ) -> Optional[Decimal]:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code (GBP, USD, EUR)
            to_currency: Target currency code
            
        Returns:
            Converted amount or None if conversion not available
        """
        if from_currency == to_currency:
            return amount
        
        # Normalize currency codes
        from_curr = from_currency.upper()
        to_curr = to_currency.upper()
        
        # Get exchange rate
        rate = cls.EXCHANGE_RATES.get((from_curr, to_curr))
        
        if rate is None:
            logger.warning(
                "exchange_rate_not_available",
                from_currency=from_curr,
                to_currency=to_curr
            )
            return None
        
        converted = amount * rate
        
        logger.debug(
            "currency_converted",
            amount=float(amount),
            from_currency=from_curr,
            to_currency=to_curr,
            rate=float(rate),
            result=float(converted)
        )
        
        return converted
    
    @classmethod
    def normalize_to_base(
        cls,
        amount: Decimal,
        currency: str,
        base_currency: str = "GBP"
    ) -> Decimal:
        """
        Normalize amount to base currency.
        
        Args:
            amount: Amount to normalize
            currency: Source currency
            base_currency: Target base currency (default: GBP)
            
        Returns:
            Amount in base currency
        """
        converted = cls.convert(amount, currency, base_currency)
        return converted if converted is not None else amount


class ScaleConverter:
    """Utility for scale conversion (millions, thousands, etc.)."""
    
    SCALE_MULTIPLIERS = {
        "actual": Decimal("1"),
        "thousands": Decimal("1000"),
        "millions": Decimal("1000000"),
        "billions": Decimal("1000000000"),
    }
    
    SCALE_ALIASES = {
        "k": "thousands",
        "m": "millions",
        "b": "billions",
        "thousand": "thousands",
        "million": "millions",
        "billion": "billions",
        "000s": "thousands",
        "000,000s": "millions",
    }
    
    @classmethod
    def normalize_scale(cls, scale: str) -> str:
        """
        Normalize scale to standard format.
        
        Args:
            scale: Scale string to normalize
            
        Returns:
            Normalized scale name
        """
        scale_lower = scale.lower().strip()
        
        # Check if already standard
        if scale_lower in cls.SCALE_MULTIPLIERS:
            return scale_lower
        
        # Check aliases
        return cls.SCALE_ALIASES.get(scale_lower, "actual")
    
    @classmethod
    def convert_to_scale(
        cls,
        amount: Decimal,
        from_scale: str,
        to_scale: str
    ) -> Decimal:
        """
        Convert amount from one scale to another.
        
        Args:
            amount: Amount to convert
            from_scale: Source scale
            to_scale: Target scale
            
        Returns:
            Converted amount
        """
        # Normalize scale names
        from_scale_norm = cls.normalize_scale(from_scale)
        to_scale_norm = cls.normalize_scale(to_scale)
        
        if from_scale_norm == to_scale_norm:
            return amount
        
        # Get multipliers
        from_multiplier = cls.SCALE_MULTIPLIERS.get(from_scale_norm, Decimal("1"))
        to_multiplier = cls.SCALE_MULTIPLIERS.get(to_scale_norm, Decimal("1"))
        
        # Convert to actual, then to target scale
        actual_value = amount * from_multiplier
        converted_value = actual_value / to_multiplier
        
        logger.debug(
            "scale_converted",
            amount=float(amount),
            from_scale=from_scale_norm,
            to_scale=to_scale_norm,
            result=float(converted_value)
        )
        
        return converted_value
    
    @classmethod
    def to_actual(cls, amount: Decimal, scale: str) -> Decimal:
        """
        Convert amount to actual (base) value.
        
        Args:
            amount: Amount in specified scale
            scale: Current scale
            
        Returns:
            Amount in actual units
        """
        return cls.convert_to_scale(amount, scale, "actual")
    
    @classmethod
    def from_actual(cls, amount: Decimal, to_scale: str) -> Decimal:
        """
        Convert actual amount to specified scale.
        
        Args:
            amount: Amount in actual units
            to_scale: Target scale
            
        Returns:
            Amount in target scale
        """
        return cls.convert_to_scale(amount, "actual", to_scale)
    
    @classmethod
    def detect_scale(cls, text: str) -> str:
        """
        Detect scale from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected scale or "actual" if not found
        """
        text_lower = text.lower()
        
        # Check for scale indicators
        if any(word in text_lower for word in ["million", "£m", "$m", "€m", "(m)"]):
            return "millions"
        elif any(word in text_lower for word in ["thousand", "£k", "$k", "€k", "(k)"]):
            return "thousands"
        elif any(word in text_lower for word in ["billion", "£b", "$b", "€b", "(b)"]):
            return "billions"
        
        return "actual"


class CurrencyDetector:
    """Utility for detecting currency from text."""
    
    CURRENCY_SYMBOLS = {
        "£": "GBP",
        "$": "USD",
        "€": "EUR",
        "¥": "JPY",
    }
    
    CURRENCY_CODES = ["GBP", "USD", "EUR", "JPY", "CHF", "CAD", "AUD"]
    
    CURRENCY_WORDS = {
        "sterling": "GBP",
        "pounds": "GBP",
        "dollars": "USD",
        "euros": "EUR",
        "euro": "EUR",
    }
    
    @classmethod
    def detect(cls, text: str) -> Optional[str]:
        """
        Detect currency from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Currency code or None if not detected
        """
        # Check for currency symbols
        for symbol, code in cls.CURRENCY_SYMBOLS.items():
            if symbol in text:
                return code
        
        # Check for currency codes
        text_upper = text.upper()
        for code in cls.CURRENCY_CODES:
            if code in text_upper:
                return code
        
        # Check for currency words
        text_lower = text.lower()
        for word, code in cls.CURRENCY_WORDS.items():
            if word in text_lower:
                return code
        
        return None


class MetricNormalizer:
    """Combined utility for normalizing financial metrics."""
    
    def __init__(self, base_currency: str = "GBP", base_scale: str = "millions"):
        """
        Initialize metric normalizer.
        
        Args:
            base_currency: Base currency for normalization
            base_scale: Base scale for normalization
        """
        self.base_currency = base_currency
        self.base_scale = base_scale
        self.currency_converter = CurrencyConverter()
        self.scale_converter = ScaleConverter()
    
    def normalize_value(
        self,
        amount: Decimal,
        currency: str,
        scale: str
    ) -> Dict[str, any]:
        """
        Normalize a metric value to base currency and scale.
        
        Args:
            amount: Original amount
            currency: Original currency
            scale: Original scale
            
        Returns:
            Dictionary with normalized value and metadata
        """
        # Convert currency
        currency_converted = self.currency_converter.convert(
            amount,
            currency,
            self.base_currency
        )
        
        if currency_converted is None:
            logger.warning(
                "currency_conversion_failed",
                currency=currency,
                base=self.base_currency
            )
            currency_converted = amount
        
        # Convert scale
        normalized_value = self.scale_converter.convert_to_scale(
            currency_converted,
            scale,
            self.base_scale
        )
        
        return {
            "original_value": amount,
            "original_currency": currency,
            "original_scale": scale,
            "normalized_value": normalized_value,
            "normalized_currency": self.base_currency,
            "normalized_scale": self.base_scale,
            "currency_converted": currency != self.base_currency,
            "scale_converted": scale != self.base_scale,
        }
