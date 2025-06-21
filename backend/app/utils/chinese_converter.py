"""
简繁体中文转换工具
"""
import opencc
from typing import List, Dict, Any



def to_simplified(text: str) -> str:
    """
    将繁体中文转换为简体中文
    
    Args:
        text: 需要转换的繁体中文文本
        
    Returns:
        转换后的简体中文文本
    """
    converter = opencc.OpenCC('t2s.json')
    return converter.convert(text)


def to_traditional(text: str) -> str:
    """
    将简体中文转换为繁体中文
    
    Args:
        text: 需要转换的简体中文文本
        
    Returns:
        转换后的繁体中文文本
    """
    converter = opencc.OpenCC('s2t.json')
    return converter.convert(text)


def convert_dict(data: Dict[str, Any], to_simple: bool = True) -> Dict[str, Any]:
    """
    转换字典中的所有字符串值
    
    Args:
        data: 需要转换的字典
        to_simple: 是否转换为简体中文，默认为True
        
    Returns:
        转换后的字典
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = to_simplified(value) if to_simple else to_traditional(value)
        elif isinstance(value, dict):
            result[key] = convert_dict(value, to_simple)
        elif isinstance(value, list):
            result[key] = convert_list(value, to_simple)
        else:
            result[key] = value
    return result


def convert_list(data: List[Any], to_simple: bool = True) -> List[Any]:
    """
    转换列表中的所有字符串值
    
    Args:
        data: 需要转换的列表
        to_simple: 是否转换为简体中文，默认为True
        
    Returns:
        转换后的列表
    """
    result = []
    for item in data:
        if isinstance(item, str):
            result.append(to_simplified(item) if to_simple else to_traditional(item))
        elif isinstance(item, dict):
            result.append(convert_dict(item, to_simple))
        elif isinstance(item, list):
            result.append(convert_list(item, to_simple))
        else:
            result.append(item)
    return result


def convert_any(data: Any, to_simple: bool = True) -> Any:
    """
    转换任何类型的数据中的所有字符串值
    
    Args:
        data: 需要转换的数据
        to_simple: 是否转换为简体中文，默认为True
        
    Returns:
        转换后的数据
    """
    if isinstance(data, str):
        return to_simplified(data) if to_simple else to_traditional(data)
    elif isinstance(data, dict):
        return convert_dict(data, to_simple)
    elif isinstance(data, list):
        return convert_list(data, to_simple)
    else:
        return data


if __name__ == '__main__':
    text = "让我们说中文"
    print(to_simplified(text))
    print(to_traditional(text))
    print(convert_dict({"key": f"{to_traditional(text)}"}))