"""Command-line interface for the AI Financial Agent."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .utils.config import get_config, set_config, Config
from .utils.logger import setup_logger, get_logger
from .workflow.graph import run_financial_agent


def setup_cli_logger(verbose: bool = False):
    """Setup logger for CLI."""
    level = "DEBUG" if verbose else "INFO"
    setup_logger(
        level=level,
        log_format="text",
        output_paths=["console", "file"],
        log_file_path="./logs/financial_agent_cli.log"
    )


def process_document(args):
    """Process a single financial document."""
    logger = get_logger({"module": "cli", "command": "process"})
    
    pdf_path = args.pdf
    output_dir = args.output or "./output"
    
    # Validate PDF exists
    if not Path(pdf_path).exists():
        logger.error("pdf_not_found", pdf_path=pdf_path)
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    logger.info("processing_document", pdf_path=pdf_path, output_dir=output_dir)
    print(f"\n{'='*60}")
    print(f"AI Financial Agent - Document Processing")
    print(f"{'='*60}")
    print(f"PDF: {pdf_path}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}\n")
    
    try:
        # Run the workflow
        result = run_financial_agent(pdf_path, output_dir)
        
        # Display results
        print(f"\n{'='*60}")
        print("Processing Complete!")
        print(f"{'='*60}")
        
        if result.get("document_metadata"):
            metadata = result["document_metadata"]
            print(f"\nDocument Information:")
            print(f"  Company: {metadata.company_name}")
            print(f"  Report Type: {metadata.report_type.value}")
            print(f"  Fiscal Period: {metadata.fiscal_period_end}")
            print(f"  Pages: {metadata.page_count}")
        
        print(f"\nExtraction Results:")
        print(f"  Text Blocks: {len(result.get('text_blocks', []))}")
        print(f"  Table Blocks: {len(result.get('table_blocks', []))}")
        print(f"  Sections Found: {len(result.get('sections', []))}")
        print(f"  Metrics Extracted: {len(result.get('validated_metrics', []))}")
        print(f"  Derived Metrics: {len(result.get('derived_metrics', []))}")
        
        if result.get("export_paths"):
            print(f"\nExported Files:")
            for file_type, file_path in result["export_paths"].items():
                print(f"  {file_type}: {file_path}")
        
        if result.get("errors"):
            print(f"\nWarnings/Errors: {len(result['errors'])}")
            for error in result["errors"][:5]:  # Show first 5
                print(f"  - {error.get('node', 'unknown')}: {error.get('error', 'unknown error')}")
        
        print(f"\n{'='*60}\n")
        logger.info("processing_completed_successfully")
        
    except Exception as e:
        logger.error("processing_failed", error=str(e))
        print(f"\nError: Processing failed: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def batch_process(args):
    """Batch process multiple documents."""
    logger = get_logger({"module": "cli", "command": "batch"})
    
    input_dir = Path(args.input_dir)
    output_dir = args.output_dir or "./output"
    
    if not input_dir.exists():
        logger.error("input_directory_not_found", input_dir=str(input_dir))
        print(f"Error: Input directory not found: {input_dir}")
        sys.exit(1)
    
    # Find all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        sys.exit(0)
    
    print(f"\n{'='*60}")
    print(f"AI Financial Agent - Batch Processing")
    print(f"{'='*60}")
    print(f"Input Directory: {input_dir}")
    print(f"Output Directory: {output_dir}")
    print(f"Files to process: {len(pdf_files)}")
    print(f"{'='*60}\n")
    
    results = []
    successful = 0
    failed = 0
    
    for idx, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{idx}/{len(pdf_files)}] Processing: {pdf_file.name}")
        logger.info("batch_processing_file", file=str(pdf_file), index=idx, total=len(pdf_files))
        
        try:
            result = run_financial_agent(str(pdf_file), output_dir)
            results.append({"file": pdf_file.name, "status": "success", "result": result})
            successful += 1
            print(f"  ✓ Success")
        except Exception as e:
            logger.error("batch_processing_file_failed", file=str(pdf_file), error=str(e))
            results.append({"file": pdf_file.name, "status": "failed", "error": str(e)})
            failed += 1
            print(f"  ✗ Failed: {str(e)}")
    
    # Summary
    print(f"\n{'='*60}")
    print("Batch Processing Complete")
    print(f"{'='*60}")
    print(f"Total: {len(pdf_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"{'='*60}\n")
    
    logger.info("batch_processing_complete", total=len(pdf_files), successful=successful, failed=failed)


def config_command(args):
    """Display or modify configuration."""
    logger = get_logger({"module": "cli", "command": "config"})
    
    if args.show:
        # Show current configuration
        config = get_config()
        
        print(f"\n{'='*60}")
        print("Current Configuration")
        print(f"{'='*60}")
        print(f"\nApplication:")
        print(f"  Name: {config.app.name}")
        print(f"  Version: {config.app.version}")
        print(f"  Environment: {config.app.environment}")
        
        print(f"\nPDF Processing:")
        print(f"  Parser Priority: {', '.join(config.pdf.parser_priority)}")
        print(f"  Timeout: {config.pdf.parser_timeout}s")
        print(f"  Max File Size: {config.pdf.max_file_size_mb}MB")
        
        print(f"\nLLM:")
        print(f"  Provider: {config.llm.provider}")
        print(f"  Model: {config.llm.model}")
        print(f"  Temperature: {config.llm.temperature}")
        
        print(f"\nValidation:")
        print(f"  YoY Growth Max: {config.validation.yoy_growth_max * 100}%")
        print(f"  YoY Growth Min: {config.validation.yoy_growth_min * 100}%")
        
        print(f"\nLogging:")
        print(f"  Level: {config.logging.level}")
        print(f"  Format: {config.logging.format}")
        print(f"{'='*60}\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Financial Agent - Intelligent financial document processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single document
  %(prog)s process --pdf annual_report_2023.pdf
  
  # Process with custom output directory
  %(prog)s process --pdf report.pdf --output ./my_output
  
  # Batch process all PDFs in a directory
  %(prog)s batch --input-dir ./pdfs --output-dir ./results
  
  # Show configuration
  %(prog)s config --show
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (default: config/config.yaml)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Process command
    process_parser = subparsers.add_parser(
        "process",
        help="Process a single financial document"
    )
    process_parser.add_argument(
        "--pdf",
        type=str,
        required=True,
        help="Path to PDF financial report"
    )
    process_parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output directory (default: ./output)"
    )
    process_parser.set_defaults(func=process_document)
    
    # Batch command
    batch_parser = subparsers.add_parser(
        "batch",
        help="Batch process multiple documents"
    )
    batch_parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing PDF files"
    )
    batch_parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory (default: ./output)"
    )
    batch_parser.set_defaults(func=batch_process)
    
    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="View or modify configuration"
    )
    config_parser.add_argument(
        "--show",
        action="store_true",
        help="Show current configuration"
    )
    config_parser.set_defaults(func=config_command)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logger
    setup_cli_logger(verbose=args.verbose)
    
    # Load custom config if specified
    if args.config:
        from .utils.config import Config
        config = Config.load_from_yaml(args.config)
        set_config(config)
    
    # Execute command
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
