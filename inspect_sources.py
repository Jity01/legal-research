"""
Utility script to inspect the structure of data source pages
This helps understand how to properly parse case information
"""
import requests
from bs4 import BeautifulSoup
import json
from config import DATA_SOURCES

def inspect_page(url, output_file=None):
    """Inspect a page structure and save HTML for analysis"""
    print(f"\n{'='*60}")
    print(f"Inspecting: {url}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Find potential case links
        print("\nPotential case-related links:")
        links = soup.find_all('a', href=True)
        case_links = []
        for link in links[:20]:  # Show first 20
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if any(keyword in href.lower() or keyword in text.lower() 
                   for keyword in ['opinion', 'case', 'docket', 'decision', 'judgment']):
                print(f"  - {text[:80]} -> {href[:100]}")
                case_links.append({'text': text, 'href': href})
        
        # Find tables (common structure for case listings)
        tables = soup.find_all('table')
        if tables:
            print(f"\nFound {len(tables)} table(s)")
            for i, table in enumerate(tables[:3]):  # Show first 3
                print(f"\nTable {i+1} structure:")
                rows = table.find_all('tr')[:5]  # First 5 rows
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        print(f"  Row: {[cell.get_text(strip=True)[:50] for cell in cells]}")
        
        # Find lists
        lists = soup.find_all(['ul', 'ol'])
        if lists:
            print(f"\nFound {len(lists)} list(s)")
            for i, lst in enumerate(lists[:3]):  # Show first 3
                items = lst.find_all('li')[:5]  # First 5 items
                if items:
                    print(f"\nList {i+1} sample items:")
                    for item in items:
                        text = item.get_text(strip=True)
                        if text and len(text) > 10:
                            print(f"  - {text[:80]}")
        
        # Find date patterns
        import re
        date_patterns = re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', response.text)
        if date_patterns:
            print(f"\nFound {len(set(date_patterns))} unique date patterns (sample):")
            for date in list(set(date_patterns))[:10]:
                print(f"  - {date}")
        
        # Save HTML for detailed inspection
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"\nHTML saved to: {output_file}")
        
        return {
            'url': url,
            'status': response.status_code,
            'case_links_count': len(case_links),
            'tables_count': len(tables),
            'lists_count': len(lists),
            'date_patterns_count': len(set(date_patterns))
        }
        
    except Exception as e:
        print(f"Error inspecting {url}: {e}")
        return None


def main():
    """Inspect all data sources"""
    print("Massachusetts Court Cases - Source Inspection Tool")
    print("=" * 60)
    
    results = []
    
    for source_name, url in DATA_SOURCES.items():
        result = inspect_page(url, output_file=f"inspect_{source_name.lower().replace(' ', '_')}.html")
        if result:
            results.append(result)
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for result in results:
        if result:
            print(f"\n{result['url']}:")
            print(f"  Status: {result['status']}")
            print(f"  Case links found: {result['case_links_count']}")
            print(f"  Tables: {result['tables_count']}")
            print(f"  Lists: {result['lists_count']}")
            print(f"  Date patterns: {result['date_patterns_count']}")


if __name__ == "__main__":
    main()
