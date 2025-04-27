from typing import Any, List, Dict

def validate_document_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize document data structure.
    Ensures that the data has a "pages" key with a list of page objects.
    Each page object should have "image_url" and "text" keys.
    
    Args:
        data: The document data dictionary
        
    Returns:
        Validated and normalized document data
    """
    if not isinstance(data, dict):
        data = {}
    
    if "pages" not in data or not isinstance(data["pages"], list):
        data["pages"] = []
    
    # Validate each page in the pages list
    validated_pages = []
    for page in data["pages"]:
        if not isinstance(page, dict):
            continue
        
        valid_page = {}
        if "image_url" in page and isinstance(page["image_url"], str):
            valid_page["image_url"] = page["image_url"]
        else:
            valid_page["image_url"] = ""
            
        if "text" in page and isinstance(page["text"], str):
            valid_page["text"] = page["text"]
        else:
            valid_page["text"] = ""
            
        validated_pages.append(valid_page)
    
    data["pages"] = validated_pages
    return data