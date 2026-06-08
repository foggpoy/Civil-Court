import json
import os
from typing import Dict, List, Any, Optional
from api.api_client import APIClient
from utils.knowledge_base import KnowledgeBase
from utils.logger import CourtLogger

class CivilCourt:

    def __init__(self, api_client: APIClient, knowledge_base: KnowledgeBase,
                 case_data: Dict[str, Any], case_id: int, output_dir: str):

        self.api_client = api_client
        self.kb = knowledge_base
        self.case_data = case_data
        self.case_id = case_id
        self.logger = CourtLogger(output_dir, case_id)

        self.profiles = self._load_profiles()

        self.retrieved_laws = {
            'judge': None,
            'plaintiff': None,
            'defendant': None
        }

    def _load_profiles(self) -> Dict[str, str]:

        profiles = {}
        profile_dir = "prompt/profile"

        for role in ['judge', 'plaintiff', 'defendant']:
            path = os.path.join(profile_dir, f"{role}.txt")
            with open(path, 'r', encoding='utf-8') as f:
                profiles[role] = f.read().strip()

        return profiles

    def _get_response(self, role: str, prompt: str, history: str = "",
                     use_profile: bool = False, use_laws: bool = False) -> str:

        full_prompt = ""

        if use_profile:
            full_prompt += self.profiles[role] + "\n\n"

        if use_laws and self.retrieved_laws.get(role):
            full_prompt += f"你可以参考以下法条：\n{self.retrieved_laws[role]}\n\n"

        if history:
            full_prompt += f"当前庭审记录：\n{history}\n\n"

        full_prompt += prompt

        messages = [{"role": "user", "content": full_prompt}]

        return self.api_client.call_role(role, messages)

    def _check_retrieve(self, role: str, memory: str) -> Optional[str]:

        with open("prompt/retrieve.txt", 'r', encoding='utf-8') as f:
            retrieve_prompt = f.read()

        retrieve_prompt = retrieve_prompt.replace("<memory>", memory)

        full_prompt = self.profiles[role] + "\n\n" + retrieve_prompt

        messages = [{"role": "user", "content": full_prompt}]

        response = self.api_client.call_role(role, messages, temperature=0.6)

        try:
            result = json.loads(response)
            if result.get('使用') == 1:
                return result.get('查询', '')
        except:
            pass

        return None

    def _summarize_stage(self, history: str) -> str:

        prompt = f"""以下是庭审记录，你要根据庭审记录，写出这一部分的庭审总结。
（1）庭审总结应当包括：按先后顺序发生的、【且可能影响最终判决的内容】的概括与总结。
程序性、重复性、与案件无关、法官控场打断等【没有实质性内容的话语】应当省略！
**注意:**
1.你只要返回这一阶段的总结即可。
2.可能涉及最后判决的重要的数字、重要信息应当保留！例如赔偿金额，证据判定等。
3.双方有争议的也要总结并保留，不能丢弃。
        庭审记录如下：
{history}"""

        messages = [{"role": "user", "content": prompt}]
        return self.api_client.call_summary(messages)

    def preparation_stage(self):

        print("\n" + "="*50)
        print("一、庭前准备阶段")
        print("="*50)

        self.logger.add_record('preparation', '审判长', '现在开庭。')
        print("审判长：现在开庭。")

        plaintiff_info = self.case_data.get('plaintiff')
        self.logger.add_record('preparation', '审判长', '请原告陈述身份信息。')
        print("审判长：请原告陈述身份信息。")

        self.logger.add_record('preparation', '原告人', plaintiff_info)
        print(f"原告人：{plaintiff_info}")

        defendant_info = self.case_data.get('defendant')
        self.logger.add_record('preparation', '审判长', '请被告陈述身份信息。')
        print("审判长：请被告陈述身份信息。")

        self.logger.add_record('preparation', '被告人', defendant_info)
        print(f"被告人：{defendant_info}")

        self.logger.add_record('preparation', '审判长', '双方对出庭人员身份是否有异议？')
        print("审判长：双方对出庭人员身份是否有异议？")

        self.logger.add_record('preparation', '原告人', '无异议。')
        print("原告人：无异议。")

        self.logger.add_record('preparation', '被告人', '无异议。')
        print("被告人：无异议。")

        self.logger.add_record('preparation', '审判长', '双方是否申请回避？')
        print("审判长：双方是否申请回避？")

        self.logger.add_record('preparation', '原告人', '不申请。')
        print("原告人：不申请。")

        self.logger.add_record('preparation', '被告人', '不申请。')
        print("被告人：不申请。")

    def investigation_stage(self):

        print("\n" + "="*50)
        print("二、法庭调查阶段")
        print("="*50)

        print("\n【原告陈述】")
        self.logger.add_record('investigation', '审判长',
                             '现在进入法庭调查阶段。首先由原告陈述诉讼请求及事实理由。')
        print("审判长：现在进入法庭调查阶段。首先由原告陈述诉讼请求及事实理由。")

        prosecution = self.case_data.get('prosecution')
        self.logger.add_record('investigation', '原告人', prosecution)
        print(f"原告人：{prosecution[:200]}..." if len(prosecution) > 200 else f"原告人：{prosecution}")

        print("\n【被告答辩】")
        self.logger.add_record('investigation', '审判长', '下面由被告进行答辩。')
        print("审判长：下面由被告进行答辩。")

        defense = self.case_data.get('defense')
        self.logger.add_record('investigation', '被告人', defense)
        print(f"被告人：{defense[:200]}..." if len(defense) > 200 else f"被告人：{defense}")

        print("\n【归纳争议焦点】")
        history = self.logger.get_stage_history('investigation')

        focus_prompt = f"""你是审判长，根据原告的起诉状和被告的答辩状，请归纳本案的争议焦点。

你需要查明案件的事实，因此争议焦点可以涵盖以下几个角度的内容：
责任认定情况：明确被告是否应对原告的损失承担责任，是否存在过错、违约或侵权行为，责任是否完全或部分归属于被告。
赔偿金额：核实损害的具体程度及赔偿金额是否合理，包括是否存在不合理的赔偿请求，是否有其他因素（如被告的经济状况、原告的损失程度等）影响赔偿数额。
案件特殊情节：例如，是否存在减轻责任或免除责任的特殊情节（如不可抗力因素、原告的部分责任、或其他缓解责任的情节），以及是否有适用的法律条文能够影响案件结果。
未充分讨论的关键问题：可能双方未讨论或尚不明确的事实或法律问题，这些问题可能对责任认定和赔偿数额有重要影响，需进一步查明并明确。

争议焦点应当具体且灵活，以确保庭审过程中的事实查明和法律适用全面公正。同时确保争议焦点表达简洁明了。

起诉状：
{prosecution}

答辩状：
{defense}

请直接返回争议焦点，每个焦点单独一行。"""

        focus = self._get_response('judge', focus_prompt)

        self.logger.add_record('investigation', '审判长',
                             f'根据双方陈述，本案的争议焦点归纳如下：\n{focus}')
        print(f"审判长：根据双方陈述，本案的争议焦点归纳如下：\n{focus}")

        print("\n【原告举证】")
        self.logger.add_record('investigation', '审判长',
                             '下面进入举证质证环节，首先由原告就案件事实向法庭综合举证，可以仅就证据的名称及所证明的事项作出说明。')
        print("审判长：下面进入举证质证环节，首先由原告就案件事实向法庭综合举证，可以仅就证据的名称及所证明的事项作出说明。")

        evidence = self.case_data.get('evidence')
        evidence_str = "审判长，原告要求出示以下证据：\n"
        for key, value in evidence.items():
            evidence_str += f"{key}：{value}\n"
        evidence_str += "请法庭组织质证。"

        self.logger.add_record('investigation', '原告人', evidence_str)
        print(f"原告人：{evidence_str[:200]}..." if len(evidence_str) > 200 else f"原告人：{evidence_str}")

        print("\n【被告质证】")
        history = self.logger.get_stage_history('investigation')

        for evidence_name, evidence_content in evidence.items():
            self.logger.add_record('investigation', '审判长',
                                 f'被告人，对原告出示的{evidence_name}有无异议？')
            print(f"审判长：被告人，对原告出示的{evidence_name}有无异议？")

            objection_prompt = f"""你是被告人，原告刚才出示了证据"{evidence_name}"，现在你要对该证据表达自己的看法。
你可以发表异议，也可以表示'没有异议'。
如果你认为该证据与本案无关，则可以提出异议；或者如果认为该证据证明效力不够，无法证明相应的结论，则可以提出异议。
注意！！
**1.所有的证据检查机关都查证了，所有证据的取得都是合理合法的，都具备有关部门的公章，取得流程符合规定，真实性、合法性无需质证！**
 **2.所有的监控、图文资料的取得也都是合法的，并且足够清楚，对这一点不需要质疑。**
**3.注意，某些证据可能和案件并非直接相关，只是描述一些背景信息，这些也不需要质证！**
**4.你也可以表示对证据的三性没有异议，但对证据的证明效力做出质疑，或者发表你对于法庭证据采信的建议。**
通常情况下，证据在庭前都经过了充分讨论，你无需质证。

如果有异议，回复"有，"后继续提出对证据的质疑；如果没有，回复'没有'。"""

            history = self.logger.get_stage_history('investigation')
            response = self._get_response('defendant', objection_prompt, history, use_profile=True)

            if response.startswith('有'):
                self.logger.add_record('investigation', '被告人', response[2:] if len(response) > 2 else response)
                print(f"被告人：{response[2:] if len(response) > 2 else response}")

                self.logger.add_record('investigation', '审判长', '原告人，被告对证据提出了异议，你是否要进行回复？')
                print("审判长：原告人，被告对证据提出了异议，你是否要进行回复？")

                reply_prompt = """你是原告人，被告对你最新提出的证据有异议，你是否要进行回复？如果要回复，回复"有，"后继续提出你的回复；如果没有，回复'没有'"""

                history = self.logger.get_stage_history('investigation')
                response = self._get_response('plaintiff', reply_prompt, history, use_profile=True)

                if response.startswith('有'):
                    self.logger.add_record('investigation', '原告人', response[2:] if len(response) > 2 else response)
                    print(f"原告人：{response[2:] if len(response) > 2 else response}")

                    judge_prompt = """你是审判长，关于这个证据控辩双方已经进行了一些辩论，你认为是否还需要进行辩论？当事情观点已经表达清楚，为了避免重复，就不用说了，否则可以继续说。如果还需要辩论，回复"是"；如果没有，回复"否"，然后对这次打断的原因做一个简单的解释。不要说多余的话！"""

                    history = self.logger.get_stage_history('investigation')
                    judge_response = self._get_response('judge', judge_prompt, history)

                    if judge_response.startswith('是'):

                        self.logger.add_record('investigation', '审判长', '被告请继续发表意见。')
                        print("审判长：被告请继续发表意见。")

                        defense_continue_prompt = """你是被告，关于这个证据，请继续发表你的辩论意见。"""
                        history = self.logger.get_stage_history('investigation')
                        defense_response = self._get_response('defendant', defense_continue_prompt, history, use_profile=True)
                        self.logger.add_record('investigation', '被告人', defense_response)
                        print(f"被告人：{defense_response}")

                        self.logger.add_record('investigation', '审判长', '原告请发表意见。')
                        print("审判长：原告请发表意见。")

                        plaintiff_continue_prompt = """你是原告，针对被告刚才的发言，请发表你的意见。"""
                        history = self.logger.get_stage_history('investigation')
                        plaintiff_response = self._get_response('plaintiff', plaintiff_continue_prompt, history, use_profile=True)
                        self.logger.add_record('investigation', '原告人', plaintiff_response)
                        print(f"原告人：{plaintiff_response}")
                    else:
                        if judge_response.startswith('否'):
                            judge_response = judge_response[2:]
                        if judge_response.strip():
                            self.logger.add_record('investigation', '审判长', judge_response)
                            print(f"审判长：{judge_response}")
                else:
                    self.logger.add_record('investigation', '原告人', '我没有要回复的。')
                    print("原告人：我没有要回复的。")
            else:
                self.logger.add_record('investigation', '被告人', '没有异议。')
                print("被告人：没有异议。")

        print("\n【庭审发问】")
        history = self.logger.get_stage_history('investigation')

        ask_prompt = f"""你是审判长，你要查明案件事实。
在举证质证阶段，你也可以对被告进行发问。
【注意】
1.你问的问题不要和法庭调查阶段重复！
2.你问的问题不要和原告、被告提出的问题重复！
3.你问的问题不要和自己之前的问题重复！

请结合当前庭审记录、拟定的辩论焦点以及当前的查明情况来决定是否询问。如果选择讯问，回复'是'后提出1个要讯问的问题；如果不询问，回复一个字'否'。"""

        response = self._get_response('judge', ask_prompt, history)

        if response.startswith('是'):
            question = response[2:] if len(response) > 2 else response
            self.logger.add_record('investigation', '审判长', question)
            print(f"审判长：{question}")

            round_num = 0
            while round_num < 5:

                answer_prompt = "目前是讯问环节，你是被告，现在你需要回复审判长刚才向你提出的问题。"
                history = self.logger.get_stage_history('investigation')
                answer = self._get_response('defendant', answer_prompt, history, use_profile=True)
                self.logger.add_record('investigation', '被告人', answer)
                print(f"被告人：{answer}")

                continue_prompt = """目前是讯问环节，你是审判长，目前你已经问了一些问题，你是否还有要继续询问的？**注意！提问的问题不要和之前自己提问的问题重复!!也不要和原告、被告提问的问题重复！!****查明即可，不要问太多问题！****注意！根据被告的回答，如果有新的疑点问题，一定要问!!!!**如果你想继续询问，回复'是'后提出1个要讯问的问题；如果选择停止讯问，回复一个字'否'。"""

                history = self.logger.get_stage_history('investigation')
                response = self._get_response('judge', continue_prompt, history)

                if not response.startswith('是'):
                    break

                question = response[2:] if len(response) > 2 else response
                self.logger.add_record('investigation', '审判长', question)
                print(f"审判长：{question}")

                round_num += 1

            self.logger.add_record('investigation', '审判长',
                                 '通过刚才的举证和质证，对于控辩双方无异议的证据，本院予以认可。对有异议的证据待合议庭评议后综合进行评判。举证质证环节结束。')
            print("审判长：通过刚才的举证和质证，对于控辩双方无异议的证据，本院予以认可。对有异议的证据待合议庭评议后综合进行评判。举证质证环节结束。")
        else:
            self.logger.add_record('investigation', '审判长',
                                 '通过刚才的举证和质证，对于控辩双方无异议的证据，本院予以认可。对有异议的证据待合议庭评议后综合进行评判。举证质证环节结束。')
            print("审判长：通过刚才的举证和质证，对于控辩双方无异议的证据，本院予以认可。对有异议的证据待合议庭评议后综合进行评判。举证质证环节结束。")

        print("\n【生成调查阶段总结】")
        history = self.logger.get_stage_history('investigation')
        summary = self._summarize_stage(history)
        self.logger.add_stage_summary('investigation', summary)
        print(f"调查阶段总结：{summary[:200]}..." if len(summary) > 200 else f"调查阶段总结：{summary}")

    def debate_stage(self):

        print("\n" + "="*50)
        print("三、法庭辩论阶段")
        print("="*50)

        self.logger.add_record('debate', '审判长',
                             '现在进入法庭辩论。控辩双方应当围绕案件事实、证据、责任认定、法律适用等进行辩论。首先由原告发表意见。')
        print("审判长：现在进入法庭辩论。控辩双方应当围绕案件事实、证据、责任认定、法律适用等进行辩论。首先由原告发表意见。")

        investigation_summary = self.logger.records['stage_summaries'].get('investigation')
        query = self._check_retrieve('plaintiff', investigation_summary)
        if query:
            print(f"\n【原告检索法条】查询：{query}")
            laws = self.kb.retrieve(query, top_k=5)
            self.retrieved_laws['plaintiff'] = self.kb.format_laws(laws)
            print(f"检索到{len(laws)}条相关法条")

        query = self._check_retrieve('defendant', investigation_summary)
        if query:
            print(f"\n【被告检索法条】查询：{query}")
            laws = self.kb.retrieve(query, top_k=5)
            self.retrieved_laws['defendant'] = self.kb.format_laws(laws)
            print(f"检索到{len(laws)}条相关法条")

        query = self._check_retrieve('judge', investigation_summary)
        if query:
            print(f"\n【法官检索法条】查询：{query}")
            laws = self.kb.retrieve(query, top_k=5)
            self.retrieved_laws['judge'] = self.kb.format_laws(laws)
            print(f"检索到{len(laws)}条相关法条")

        print("\n【原告发表意见】")
        plaintiff_prompt = f"""作为原告人，你需要根据已展示的庭审记录、起诉状、证据、被告信息等，对本案进行总体论述，力求公正判决。直接返回你的发言内容。
【注意】：
1.开头先做一下简要介绍。例如：审判长，根据中华人民共和国民事诉讼法的规定，我作为原告，现就本案事实及法律依据发表如下意见。
2.你的意见应当至少包含【案件事实】、【法律依据】、【诉讼请求】，缺一不可。
3.你的意见也应当融入前文的一些总结，对前文争议异议内容的回应。
4.你的意见应当【全面】，且有理有据，发表观点的同时应当引用本案的证据、以及法庭中的发言内容。所有要说的指控观点一并论述出来。
5.在诉讼请求方面，还要引用法律条文支持。
6.最后可以对案件做适当的总结陈述。

你的内容分点不要用阿拉伯数字，用自然语言描述即可。例如第一、第二、首先、其次、最后，等等

起诉状：
{self.case_data.get('prosecution')}"""

        history = self.logger.get_stage_history('debate')
        response = self._get_response('plaintiff', plaintiff_prompt, history,
                                     use_profile=True, use_laws=True)
        self.logger.add_record('debate', '原告人', response)
        print(f"原告人：{response[:300]}..." if len(response) > 300 else f"原告人：{response}")

        print("\n【被告发表辩护意见】")
        self.logger.add_record('debate', '审判长', '下面由被告发表意见。')
        print("审判长：下面由被告发表意见。")

        defense_prompt = f"""作为被告人，你需要根据已展示的庭审记录、起诉状、答辩状、证据等，对本案进行总体论述，力求减轻责任。直接返回你的发言内容。

【注意】：
1.开头先做一下简要介绍。例如：尊敬的审判长，我作为被告，现就本案事实依法作如下辩护。
2.你的辩护意见应当至少包含【案件事实】、【法律依据】、【辩护观点】，缺一不可。并且要注意逻辑，回应原告的意见。
3.你的意见也应当融入前文的一些总结，对前文争议异议内容的回应。
4.你的辩护意见应当全面，且有理有据，发表观点的同时应当引用本案的证据、以及法庭中的发言内容。所有要说的辩护观点一并论述出来。
5.在辩护观点方面，还要引用法律条文支持。
6.不要仅自顾自地发言，要回应原告的意见。

你的内容分点不要用阿拉伯数字，用自然语言描述即可。例如第一、第二、首先、其次、最后，等等

答辩状：
{self.case_data.get('defense')}"""

        history = self.logger.get_stage_history('debate')
        response = self._get_response('defendant', defense_prompt, history,
                                     use_profile=True, use_laws=True)
        self.logger.add_record('debate', '被告人', response)
        print(f"被告人：{response[:300]}..." if len(response) > 300 else f"被告人：{response}")

        print("\n【双方补充意见】")
        for round_num in range(1):

            self.logger.add_record('debate', '审判长', '原告是否还有补充的意见？')
            print("审判长：原告是否还有补充的意见？")

            supplement_prompt = """你是原告人，请根据被告的辩护意见，决定是否需要补充发言。注意，为了避免重复，如果你的意见都已经发表完毕了，直接回复没有其他意见即可。如果要补充，请简明扼要地回应被告的观点。"""

            history = self.logger.get_stage_history('debate')
            response = self._get_response('plaintiff', supplement_prompt, history,
                                         use_profile=True, use_laws=True)
            self.logger.add_record('debate', '原告人', response)
            print(f"原告人：{response[:200]}..." if len(response) > 200 else f"原告人：{response}")

            self.logger.add_record('debate', '审判长', '被告是否还有补充的意见？')
            print("审判长：被告是否还有补充的意见？")

            supplement_prompt = """现在是法庭辩论，你可以发表意见，也可以不发表意见。注意，为了避免重复，如果你的意见都已经发表完毕了，直接回复没有其他意见即可。通常情况下，你可以不发表意见。"""

            history = self.logger.get_stage_history('debate')
            response = self._get_response('defendant', supplement_prompt, history,
                                         use_profile=True, use_laws=False)
            self.logger.add_record('debate', '被告人', response)
            print(f"被告人：{response[:200]}..." if len(response) > 200 else f"被告人：{response}")

        print("\n【法官检查辩论要点】")
        for _ in range(5):
            check_prompt = """作为审判长，法庭辩论环节是你【最后】查清案件事实的机会。请你根据【争议焦点】、【查明情况】、【以及当前辩论中双方没有达成一致看法的要点】，思考是否还存在**关键的**、未查明的、且和案件有关的事实。
如果有，你应当组织新的辩论焦点，以便查清案件事实。特别是你本来就认为需要进一步讨论的焦点，应当组织双方进行辩论。

如果你认为还需要进行针对新的要点进行辩论，**请回复'是，'，并紧接着提出具体要点**；如果你认为不需要了（比如双方已经达成共识，或者你心里已有答案），请回复'否'。

例如：
（当你发现被告是否应承担责任是关键问题，但双方还没有达成一致）
是，双方对被告是否应承担责任还存在异议，请双方针对此问题进行进一步讨论。

注意：
1.法庭辩论环节是你【最后】查清案件事实的机会！对关键的且双方仍然有争议的部分一定要组织进一步的辩论！
2.你当前要辩论的要点不能和之前辩论的要点重复！
"""

            history = self.logger.get_stage_history('debate')
            response = self._get_response('judge', check_prompt, history)

            if response.startswith('是'):
                new_focus = response[2:] if len(response) > 2 else response

                intro_prompt = f"当前要讨论的焦点是'{new_focus}'，请承上启下地引出这一个焦点，并让原告先发言。注意要说一句通顺的话。例如：方才双方针对xxx已经发表了一些意见，接下来的辩论请围绕xxxx进行展开，由原告先发言。"
                intro = self._get_response('judge', intro_prompt, "", use_profile=False, use_laws=False)
                self.logger.add_record('debate', '审判长', intro)
                print(f"审判长：{intro}")

                plaintiff_focus_prompt = f"作为原告人，请针对{new_focus}这一要点及被告的论述进行论述或回应。"
                history = self.logger.get_stage_history('debate')
                response = self._get_response('plaintiff', plaintiff_focus_prompt, history,
                                             use_profile=True, use_laws=True)
                self.logger.add_record('debate', '原告人', response)
                print(f"原告人：{response[:200]}..." if len(response) > 200 else f"原告人：{response}")

                self.logger.add_record('debate', '审判长', '下面由被告发表意见。')
                print("审判长：下面由被告发表意见。")

                defendant_defense_prompt = f"作为被告人，请针对{new_focus}这一要点及原告的论述进行论述或回应。"
                history = self.logger.get_stage_history('debate')
                response = self._get_response('defendant', defendant_defense_prompt, history,
                                             use_profile=True, use_laws=True)
                self.logger.add_record('debate', '被告人', response)
                print(f"被告人：{response[:200]}..." if len(response) > 200 else f"被告人：{response}")

                while True:
                    continue_prompt = f"目前讨论的焦点是：{new_focus}。作为审判长，请你根据最近的庭审记录，裁定该辩论焦点是否还需要继续讨论。如果已经讨论清楚，或者双方的发言明显重复或没有进展，则不必继续讨论了。如果还需要讨论，请回复'是'；如果不需要讨论，请回复'否'。"

                    history = self.logger.get_stage_history('debate')
                    judge_response = self._get_response('judge', continue_prompt, history)

                    if not judge_response.startswith('是'):
                        break

                    self.logger.add_record('debate', '审判长', '原告是否还有补充的意见？')
                    print("审判长：原告是否还有补充的意见？")

                    supplement_prompt = f"作为原告人，请针对{new_focus}这一要点及被告的论述进行论述或回应。注意，为了避免重复，如果你的意见都已经发表完毕了，直接回复没有其他意见即可。"
                    history = self.logger.get_stage_history('debate')
                    response = self._get_response('plaintiff', supplement_prompt, history,
                                                 use_profile=True, use_laws=True)
                    self.logger.add_record('debate', '原告人', response)
                    print(f"原告人：{response[:200]}..." if len(response) > 200 else f"原告人：{response}")

                    self.logger.add_record('debate', '审判长', '被告是否还有补充的意见？')
                    print("审判长：被告是否还有补充的意见？")

                    defense_supplement_prompt = f"作为被告人，请针对{new_focus}这一要点及原告的论述进行论述或回应。注意，为了避免重复，如果你的意见都已经发表完毕了，直接回复没有其他意见即可。"
                    history = self.logger.get_stage_history('debate')
                    response = self._get_response('defendant', defense_supplement_prompt, history,
                                                 use_profile=True, use_laws=True)
                    self.logger.add_record('debate', '被告人', response)
                    print(f"被告人：{response[:200]}..." if len(response) > 200 else f"被告人：{response}")
            else:
                break

        self.logger.add_record('debate', '审判长',
                             '经过法庭辩论，双方均已充分发表意见，本庭已经听清并记录在案，合议庭在评议时会充分考虑。法庭辩论结束。')
        print("审判长：经过法庭辩论，双方均已充分发表意见，本庭已经听清并记录在案，合议庭在评议时会充分考虑。法庭辩论结束。")

        print("\n【生成辩论阶段总结】")
        history = self.logger.get_stage_history('debate')
        summary = self._summarize_stage(history)
        self.logger.add_stage_summary('debate', summary)
        print(f"辩论阶段总结：{summary[:200]}..." if len(summary) > 200 else f"辩论阶段总结：{summary}")

    def final_statement_stage(self):

        print("\n" + "="*50)
        print("四、最后陈述阶段")
        print("="*50)

        self.logger.add_record('final_statement', '审判长',
                             '法庭辩论结束后，现在请双方发表最后陈述意见。原告，请陈述你的意见。')
        print("审判长：法庭辩论结束后，现在请双方发表最后陈述意见。原告，请陈述你的意见。")

        self.logger.add_record('final_statement', '原告人', '请求支持原告诉讼请求。')
        print("原告人：请求支持原告诉讼请求。")

        self.logger.add_record('final_statement', '审判长', '被告，请陈述你的意见。')
        print("审判长：被告，请陈述你的意见。")

        self.logger.add_record('final_statement', '被告人', '依法判决。')
        print("被告人：依法判决。")

    def judgement_stage(self):

        print("\n" + "="*50)
        print("五、判决阶段")
        print("="*50)

        investigation_summary = self.logger.records['stage_summaries'].get('investigation')
        debate_summary = self.logger.records['stage_summaries'].get('debate')
        memory = investigation_summary + "\n\n" + debate_summary

        print("\n【法官检索法条用于判决】")
        query = self._check_retrieve('judge', memory)
        if query:
            print(f"查询：{query}")
            laws = self.kb.retrieve(query, top_k=10)
            law_text = self.kb.format_laws(laws)
            print(f"检索到{len(laws)}条相关法条")
        else:
            law_text = ""
            print("法官决定不检索法条")

        with open("prompt/judgement.txt", 'r', encoding='utf-8') as f:
            judgement_prompt = f.read()

        fact = self.case_data.get('fact')
        judgement_prompt = judgement_prompt.replace("<fact>", fact)
        judgement_prompt = judgement_prompt.replace("<memory>", memory)

        if law_text:
            judgement_prompt += f"\n\n参考法条：\n{law_text}"

        print("\n【生成判决】")
        messages = [{"role": "user", "content": judgement_prompt}]
        judgement = self.api_client.call_deepseek(messages, temperature=0.6)

        self.logger.add_record('judgement', '审判长', judgement)
        self.logger.add_stage_summary('judgement', judgement)

        print(f"审判长：{judgement[:500]}..." if len(judgement) > 500 else f"审判长：{judgement}")

        print("\n判决完成！")

    def run(self):

        try:
            print(f"\n{'='*60}")
            print(f"开始模拟案件 ID: {self.case_id}")
            print(f"{'='*60}\n")

            self.preparation_stage()

            self.investigation_stage()

            self.debate_stage()

            self.final_statement_stage()

            self.judgement_stage()

            self.logger.finalize()

            print(f"\n{'='*60}")
            print(f"案件 ID {self.case_id} 模拟完成！")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"\n案件 {self.case_id} 模拟过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            self.logger.finalize()
