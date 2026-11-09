from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union

# 测试用例条目：断言字符串（MBPP 等）或 {input, output, ...} 结构（自定义题）
TestCase = Union[str, Dict[str, Any]]

# 创建题目入参模型
class ProblemCreate(BaseModel):
    dataset_name: str
    subset: Optional[str] = None
    title: Optional[str] = None
    prompt: str
    test_cases: List[TestCase]
    test_imports: Optional[List[str]] = None
    reference_solution: Optional[str] = None
    difficulty: Optional[str] = None

# 更新题目入参模型：全部字段可选，配合 exclude_unset 做局部更新
class ProblemUpdate(BaseModel):
    dataset_name: Optional[str] = None
    subset: Optional[str] = None
    title: Optional[str] = None
    prompt: Optional[str] = None
    test_cases: Optional[List[TestCase]] = None
    test_imports: Optional[List[str]] = None
    reference_solution: Optional[str] = None
    difficulty: Optional[str] = None

# 返回模型
class Problem(ProblemCreate):
    id: int
    created_at: str
    updated_at: str
