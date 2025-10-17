"""
LLM API 兼容性工具

处理不同 LLM 提供商和模型版本之间的参数差异。
"""

from typing import Dict, Any


def prepare_llm_params(
    model: str,
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 16384,  # 🔧 修复默认值从 2048 提升到 16384
    **kwargs
) -> Dict[str, Any]:
    """
    准备 LLM API 调用参数，自动处理不同模型的参数兼容性
    
    Args:
        model: 模型名称
        messages: 对话消息列表
        temperature: 温度参数（某些模型不支持会被忽略）
        max_tokens: 最大 token 数（默认 16384）
        **kwargs: 其他额外参数
    
    Returns:
        适配后的参数字典
    
    Examples:
        >>> params = prepare_llm_params("gpt-5-mini", messages, max_tokens=100)
        >>> # 返回 {"model": "gpt-5-mini", "messages": [...], "max_completion_tokens": 100, ...}
        
        >>> params = prepare_llm_params("gpt-5-pro", messages, max_tokens=100)
        >>> # 返回 {"model": "gpt-5-pro", "messages": [...], "max_completion_tokens": 100}
        >>> # 注意：gpt-5-pro 不支持 temperature，所以不包含该参数
        
        >>> params = prepare_llm_params("gpt-4", messages, max_tokens=100)
        >>> # 返回 {"model": "gpt-4", "messages": [...], "max_tokens": 100, "temperature": 0.7}
    """
    params = {
        "model": model,
        "messages": messages,
    }
    
    # 获取模型特性
    features = get_model_features(model)
    
    # GPT-5 系列不传 temperature，使用 API 默认值
    # 其他模型（如 GPT-4）才支持自定义 temperature
    if features.get("supports_temperature", True) and not model.startswith("gpt-5"):
        params["temperature"] = temperature
    
    # GPT-5 系列模型使用 max_completion_tokens
    if model.startswith("gpt-5"):
        params["max_completion_tokens"] = max_tokens
    # GPT-4 及更早版本使用 max_tokens
    else:
        params["max_tokens"] = max_tokens
    
    # 添加其他参数
    params.update(kwargs)
    
    return params


def is_gpt5_model(model: str) -> bool:
    """
    判断是否为 GPT-5 系列模型
    
    Args:
        model: 模型名称
    
    Returns:
        True 如果是 GPT-5 系列，False 否则
    """
    return model.startswith("gpt-5")


def get_max_tokens_param_name(model: str) -> str:
    """
    获取模型的 max_tokens 参数名
    
    Args:
        model: 模型名称
    
    Returns:
        参数名称字符串
    """
    if is_gpt5_model(model):
        return "max_completion_tokens"
    return "max_tokens"


# 模型特性映射
MODEL_FEATURES = {
    # GPT-5 系列 - 注意：gpt-5-pro 不支持 temperature 参数
    "gpt-5-pro": {
        "max_tokens_param": "max_completion_tokens",
        "supports_temperature": False,  # gpt-5-pro 不支持 temperature
        "supports_vision": True,
        "supports_function_calling": True,
        "max_context": 128000,
    },
    "gpt-5-mini": {
        "max_tokens_param": "max_completion_tokens",
        "supports_temperature": True,
        "supports_vision": True,
        "supports_function_calling": True,
        "max_context": 128000,
    },
    "gpt-5-chat-latest": {
        "max_tokens_param": "max_completion_tokens",
        "supports_temperature": True,
        "supports_vision": True,
        "supports_function_calling": True,
        "max_context": 128000,
    },
    "gpt-5-nano": {
        "max_tokens_param": "max_completion_tokens",
        "supports_temperature": True,
        "supports_vision": False,
        "supports_function_calling": True,
        "max_context": 32000,
    },
    
    # GPT-4 系列（兼容）
    "gpt-4": {
        "max_tokens_param": "max_tokens",
        "supports_temperature": True,
        "supports_vision": False,
        "supports_function_calling": True,
        "max_context": 8192,
    },
    "gpt-4-turbo": {
        "max_tokens_param": "max_tokens",
        "supports_temperature": True,
        "supports_vision": True,
        "supports_function_calling": True,
        "max_context": 128000,
    },
    
    # GPT-3.5 系列（兼容）
    "gpt-3.5-turbo": {
        "max_tokens_param": "max_tokens",
        "supports_temperature": True,
        "supports_vision": False,
        "supports_function_calling": True,
        "max_context": 16385,
    },
}


def get_model_features(model: str) -> Dict[str, Any]:
    """
    获取模型特性
    
    Args:
        model: 模型名称
    
    Returns:
        模型特性字典
    """
    # 精确匹配
    if model in MODEL_FEATURES:
        return MODEL_FEATURES[model]
    
    # 前缀匹配
    for model_prefix, features in MODEL_FEATURES.items():
        if model.startswith(model_prefix):
            return features
    
    # 默认特性（GPT-4 类似）
    return {
        "max_tokens_param": "max_tokens",
        "supports_temperature": True,  # 默认支持
        "supports_vision": False,
        "supports_function_calling": True,
        "max_context": 8192,
    }


def validate_model_params(model: str, **params) -> Dict[str, Any]:
    """
    验证并调整模型参数
    
    Args:
        model: 模型名称
        **params: 参数字典
    
    Returns:
        验证并调整后的参数
    """
    features = get_model_features(model)
    validated_params = params.copy()
    
    # 调整 max_tokens 参数名
    if "max_tokens" in validated_params:
        max_tokens_value = validated_params.pop("max_tokens")
        correct_param_name = features["max_tokens_param"]
        validated_params[correct_param_name] = max_tokens_value
    
    # 限制 max_tokens 不超过上下文长度
    max_tokens_param = features["max_tokens_param"]
    if max_tokens_param in validated_params:
        validated_params[max_tokens_param] = min(
            validated_params[max_tokens_param],
            features["max_context"] // 2  # 留一半给输入
        )
    
    return validated_params


if __name__ == "__main__":
    # 测试示例
    print("=" * 60)
    print("LLM 参数兼容性测试")
    print("=" * 60)
    
    test_messages = [
        {"role": "user", "content": "Hello"}
    ]
    
    # 测试 GPT-5
    print("\n1. GPT-5-mini:")
    params = prepare_llm_params("gpt-5-mini", test_messages, max_tokens=100)
    print(f"   参数: {params}")
    print(f"   max_tokens 参数名: {get_max_tokens_param_name('gpt-5-mini')}")
    
    # 测试 GPT-4
    print("\n2. GPT-4:")
    params = prepare_llm_params("gpt-4", test_messages, max_tokens=100)
    print(f"   参数: {params}")
    print(f"   max_tokens 参数名: {get_max_tokens_param_name('gpt-4')}")
    
    # 测试特性获取
    print("\n3. 模型特性:")
    for model in ["gpt-5-pro", "gpt-5-mini", "gpt-4", "gpt-3.5-turbo"]:
        features = get_model_features(model)
        print(f"   {model}:")
        print(f"     - max_tokens 参数: {features['max_tokens_param']}")
        print(f"     - 最大上下文: {features['max_context']}")
    
    print("\n✅ 测试完成")
