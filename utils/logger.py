import json
import os
from typing import Dict, Any, List
from datetime import datetime

class CourtLogger:

    def __init__(self, output_dir: str, case_id: int):

        self.output_dir = output_dir
        self.case_id = case_id
        self.records = {
            'case_id': case_id,
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stages': {
                'preparation': [],
                'investigation': [],
                'debate': [],
                'final_statement': [],
                'judgement': []
            },
            'stage_summaries': {}
        }

        os.makedirs(output_dir, exist_ok=True)

    def add_record(self, stage: str, role: str, content: str):

        record = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        if stage in self.records['stages']:
            self.records['stages'][stage].append(record)
            self._save()

    def add_stage_summary(self, stage: str, summary: str):

        self.records['stage_summaries'][stage] = summary
        self._save()

    def get_stage_history(self, stage: str) -> str:

        if stage not in self.records['stages']:
            return ""

        history_lines = []
        for record in self.records['stages'][stage]:
            history_lines.append(f"{record['role']}：{record['content']}")

        return "\n".join(history_lines)

    def get_all_summaries(self) -> str:

        summaries = []
        for stage, summary in self.records['stage_summaries'].items():
            if summary:
                summaries.append(f"【{stage}阶段庭审总结】\n{summary}")
        return "\n\n".join(summaries)

    def _save(self):

        output_path = os.path.join(self.output_dir, f"case_{self.case_id}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)

    def finalize(self):

        self.records['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._save()
        print(f"案件 {self.case_id} 的庭审记录已保存到: {self.output_dir}/case_{self.case_id}.json")
