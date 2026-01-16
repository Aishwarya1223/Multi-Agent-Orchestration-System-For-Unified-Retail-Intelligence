# agents/langchain_based_agents/vision_agent.py

from langchain_core.tools import tool
from langchain.agents import create_agent
from omniflow.agents.langchain_based_agents.base import get_llm, get_system_prompt, mcp_manager
import base64
import re
from PIL import Image
import io

def analyze_image_func(image_data: str, query: str = "What do you see in this image?") -> dict:
    """
    Analyze an image and provide description.
    image_data should be base64 encoded string.
    """
    try:
        # Extract base64 data from data URL
        if image_data.startswith('data:image'):
            # Remove data URL prefix
            base64_string = re.sub(r'^data:image/.+;base64,', '', image_data)
        else:
            base64_string = image_data
        
        # Decode base64 to bytes
        image_bytes = base64.b64decode(base64_string)
        
        # For now, return basic image info
        # In a real implementation, you'd use OpenAI Vision API or similar
        image = Image.open(io.BytesIO(image_bytes))
        
        return {
            "description": f"This appears to be a {image.format} image with dimensions {image.size[0]}x{image.size[1]} pixels. Mode: {image.mode}.",
            "format": image.format,
            "size": image.size,
            "mode": image.mode,
            "query_response": f"Based on the image and your query '{query}', I can see this is an image that needs further analysis with a proper vision model."
        }
        
    except Exception as e:
        return {
            "error": f"Failed to analyze image: {str(e)}",
            "description": "Unable to process the image. Please ensure it's a valid image file."
        }

def identify_product_from_image_func(image_data: str) -> dict:
    """
    Try to identify products from an image using visual cues.
    """
    try:
        # Extract base64 data
        if image_data.startswith('data:image'):
            base64_string = re.sub(r'^data:image/.+;base64,', '', image_data)
        else:
            base64_string = image_data
        
        image_bytes = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Mock product identification based on image characteristics
        # In real implementation, use computer vision models
        width, height = image.size
        
        # Simple heuristics for demo
        if width > 1000 and height > 1000:
            product_type = "Large Electronic Device"
            confidence = 0.7
        elif width > 500 and height > 500:
            product_type = "Medium Electronic Device"
            confidence = 0.6
        else:
            product_type = "Small Electronic Device"
            confidence = 0.5
            
        return {
            "product_type": product_type,
            "confidence": confidence,
            "image_size": f"{width}x{height}",
            "suggested_products": ["Gaming Monitor", "Laptop", "Smartphone"],
            "note": "This is a mock implementation. Real product identification would require trained vision models."
        }
        
    except Exception as e:
        return {
            "error": f"Failed to identify product: {str(e)}",
            "product_type": "Unknown",
            "confidence": 0.0
        }

# Create LangChain tools
analyze_image = tool(analyze_image_func)
identify_product_from_image = tool(identify_product_from_image_func)

@tool
async def mcp_vision_analysis(image_data: str, query: str) -> dict:
    """
    Analyze image via MCP server if available.
    """
    try:
        # Try to get vision analysis from MCP server
        result = await mcp_manager.call_tool("vision_service", "analyze_image", {
            "image_data": image_data,
            "query": query
        })
        return result.content if hasattr(result, 'content') else result
    except:
        # Fallback to local analysis
        return analyze_image_func(image_data, query)

def build_vision_agent():
    llm = get_llm()
    prompt = get_system_prompt("Vision Agent")

    agent = create_agent(
        model=llm,
        tools=[analyze_image, identify_product_from_image, mcp_vision_analysis],
        system_prompt=prompt
    )

    return agent
