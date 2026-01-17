"""
Main entry point for collecting Massachusetts court cases
"""
import argparse
import logging
from datetime import datetime
from case_collector import CaseCollector
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Collect Massachusetts court cases since 1900')
    parser.add_argument('--start-year', type=int, default=config.START_YEAR,
                       help=f'Start year for collection (default: {config.START_YEAR})')
    parser.add_argument('--end-year', type=int, default=config.END_YEAR,
                       help=f'End year for collection (default: {config.END_YEAR})')
    parser.add_argument('--stats', action='store_true',
                       help='Show collection statistics')
    parser.add_argument('--court-type', type=str, choices=list(config.COURT_TYPES.keys()),
                       help='Filter by specific court type')
    
    args = parser.parse_args()
    
    collector = CaseCollector()
    
    if args.stats:
        stats = collector.get_statistics()
        print("\n=== Collection Statistics ===")
        print(f"Total cases: {stats['total_cases']}")
        print("\nBy Court Type:")
        for court, count in sorted(stats['by_court'].items()):
            print(f"  {court}: {count}")
        print("\nBy Year (sample):")
        for year in sorted(stats['by_year'].keys())[:20]:
            print(f"  {year}: {stats['by_year'][year]}")
        return
    
    logger.info("Starting Massachusetts court case collection")
    logger.info(f"Date range: {args.start_year} - {args.end_year}")
    
    try:
        total = collector.collect_all(start_year=args.start_year, end_year=args.end_year)
        logger.info(f"Collection completed. Total cases collected: {total}")
        
        # Show statistics
        stats = collector.get_statistics()
        print(f"\nTotal cases in database: {stats['total_cases']}")
        
    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
    except Exception as e:
        logger.error(f"Collection failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
