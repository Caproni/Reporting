#!/usr/local/bin/python
"""
Author: Edmund Bennett
Copyright 2024
"""

from typing import Any
import re

from .get_data_from_tag import get_data_from_tag
from src.utils import logger as log


def process_tag(
    tag: str,
    data: list[dict[str, Any]],
):
    """
    Recursive function to process a tag and return its content.
    If the tag contains one or more other tag, it processes the inner tags first.

    Args:
        tag (str): The tag to process, e.g. '{{Report_Title}}' or '{{Outer_Tag {{Inner_Tag}}}}'.
        data (dict): A dictionary containing tag-to-content mapping.

    Returns:
        str: The processed content with inner tags replaced.
    """
    log.function_call()

    tag_pattern: str = r"\[\[(.*?)\]\]"

    if not re.search(tag_pattern, tag):
        return get_data_from_tag(
            tag=tag,
            data=data,
        )

    while re.search(tag_pattern, tag):
        inner_tag = re.search(tag_pattern, tag)[0]
        inner_content = process_tag(inner_tag, data)
        tag = tag.replace(inner_tag, inner_content)

    return tag
