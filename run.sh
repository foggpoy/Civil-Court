#!/bin/bash

if [ $# -lt 2 ]; then
    echo "使用方法: ./run.sh <起始索引> <结束索引> [可选模型参数]"
    echo "示例: ./run.sh 0 4"
    echo "      ./run.sh 0 0"
    exit 1
fi

START_IDX=$1
END_IDX=$2

if ! [[ "$START_IDX" =~ ^[0-9]+$ ]] || ! [[ "$END_IDX" =~ ^[0-9]+$ ]]; then
    echo "错误: 索引必须是非负整数"
    exit 1
fi

if [ $START_IDX -gt $END_IDX ]; then
    echo "错误: 起始索引不能大于结束索引"
    exit 1
fi

echo "======================================"
echo "民事模拟法庭系统"
echo "======================================"
echo "运行案件范围: 索引 $START_IDX 到 $END_IDX"
echo "======================================"
echo ""

cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

if [ ! -f "run.py" ]; then
    echo "错误: 未找到 run.py"
    exit 1
fi

if [ ! -f "data/selected_cases.jsonl" ]; then
    echo "错误: 未找到数据文件 data/selected_cases.jsonl"
    exit 1
fi

if [ ! -f "data/law_library.jsonl" ]; then
    echo "错误: 未找到法条库文件 data/law_library.jsonl"
    exit 1
fi

mkdir -p output

echo "开始运行模拟法庭..."
echo ""

python3 run.py "$START_IDX" "$END_IDX" "${@:3}"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "======================================"
    echo "模拟法庭运行完成！"
    echo "结果已保存到 output/ 目录"
    echo "======================================"
else
    echo "======================================"
    echo "模拟法庭运行出错，退出码: $EXIT_CODE"
    echo "======================================"
fi

exit $EXIT_CODE
