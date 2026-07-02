import os
import re
import json
from typing import Any, Dict
import requests


class QwenClient:
    def __init__(self):
        self.api_key = os.getenv("QWEN_API_KEY", "").strip()
        self.base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").strip()
        self.model = os.getenv("QWEN_MODEL", "qwen-max").strip()
        self.demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"

    def test_connection(self) -> Dict[str, Any]:
        if self._use_mock():
            return {"status": "ok", "message": "demo mode: qwen key not required"}
        return self.chat_json('请只输出严格 JSON：{"status":"ok","message":"qwen api works"}')

    def parse_requirement(self, text: str) -> Dict[str, Any]:
        if self._use_mock():
            return self._mock_parse_requirement(text)
        prompt = f"""
把下面热仿真需求抽取为严格 JSON，只输出 JSON。
字段：
ambient_temperature_c, heat_source_power_w, inlet_velocity_m_s,
max_allowed_temperature_c, material_hint, product_type, simulation_goal,
missing_fields, requires_review。

需求：
{text}
"""
        return self.chat_json(prompt)

    def make_optimization_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self._use_mock():
            return self._mock_optimization_plan(context)
        prompt = f"""
你是受控热仿真优化 Agent。根据 optimization_context 生成严格 JSON。
必须遵守：
1. 只能使用 optimization_rules.design_levers 里的参数。
2. 不能超过 min/max/allowed_values。
3. 涉及几何、材料的改动必须 requires_review=true。
4. 输出必须包含 diagnosis, changes, risk_level, requires_review, expected_effect, recommended_next_tool。
5. 不要输出解释文字，只输出 JSON。

optimization_context:
{json.dumps(context, ensure_ascii=False)}
"""
        return self.chat_json(prompt)

    def chat_json(self, prompt: str) -> Dict[str, Any]:
        if not self.api_key or self.api_key.startswith("请替换"):
            raise RuntimeError("Missing QWEN_API_KEY. Use DEMO_MODE=true for local mock.")
        url = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You output strict JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Qwen API error: {resp.status_code} {resp.text}")
        content = resp.json()["choices"][0]["message"]["content"]
        return self._json_from_text(content)

    def _json_from_text(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, re.S)
            if not m:
                raise RuntimeError(f"Qwen did not return JSON: {text}")
            return json.loads(m.group(0))

    def _use_mock(self) -> bool:
        return self.demo_mode and (not self.api_key or self.api_key.startswith("请替换"))

    def _mock_parse_requirement(self, text: str) -> Dict[str, Any]:
        def find_num(patterns, default):
            for p in patterns:
                m = re.search(p, text, re.I)
                if m:
                    return float(m.group(1))
            return default
        ambient = find_num([r"环境温度\s*(\d+)", r"ambient.*?(\d+)"], 45)
        power = find_num([r"功耗\s*(\d+)", r"(\d+)\s*W", r"power.*?(\d+)"], 80)
        velocity = find_num([r"风速\s*(\d+(?:\.\d+)?)", r"velocity.*?(\d+(?:\.\d+)?)"], 2)
        target = find_num([r"最高温度.*?(\d+)", r"低于\s*(\d+)", r"under\s*(\d+)"], 95)
        material_hint = "铝合金" if ("铝" in text or "aluminum" in text.lower()) else ""
        return {
            "ambient_temperature_c": ambient,
            "heat_source_power_w": power,
            "inlet_velocity_m_s": velocity,
            "max_allowed_temperature_c": target,
            "material_hint": material_hint,
            "product_type": "plate_fin_heatsink",
            "simulation_goal": f"max temperature <= {target} C",
            "missing_fields": [],
            "requires_review": True
        }

    def _mock_optimization_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        result = context.get("current_result", {})
        config = context.get("current_config", {})
        rules = context.get("optimization_rules", {})
        levers = rules.get("design_levers", {})
        max_temp = float(result.get("max_temperature_c", 999))
        target = float(result.get("target_max_temperature_c", 95))
        pressure_drop = float(result.get("pressure_drop_pa", 999))
        changes = []
        diagnosis = "passed"
        risk_level = "low"
        requires_review = False
        if max_temp > target:
            diagnosis = "design_failed_temperature_too_high"
            if "inlet_velocity_m_s" in levers and pressure_drop < 80:
                lever = levers["inlet_velocity_m_s"]
                old = config.get("boundary_conditions", {}).get("inlet", {}).get("velocity_m_s", lever.get("current_default", 2))
                new = min(lever["max"], old + lever["step"])
                if new > old:
                    changes.append({
                        "parameter": "inlet_velocity_m_s",
                        "old_value": old,
                        "new_value": new,
                        "reason": "超温且压降低，先增加风速提升对流换热。",
                        "requires_geometry_change": False,
                        "requires_review": bool(lever.get("requires_approval", False))
                    })
            if "fin_height_mm" in levers:
                lever = levers["fin_height_mm"]
                old = config.get("design_variables", {}).get("fin_height_mm", lever.get("current_default", 18))
                new = min(lever["max"], old + 4)
                if new > old:
                    changes.append({
                        "parameter": "fin_height_mm",
                        "old_value": old,
                        "new_value": new,
                        "reason": "超温，增加鳍片高度提升散热面积。",
                        "requires_geometry_change": True,
                        "requires_review": True
                    })
                    risk_level = "medium"
                    requires_review = True
        return {
            "diagnosis": diagnosis,
            "confidence": 0.65,
            "changes": changes,
            "risk_level": risk_level,
            "requires_review": requires_review or any(c.get("requires_review") for c in changes),
            "expected_effect": {"temperature_reduction_direction": "down", "pressure_drop_direction": "up_or_same"},
            "recommended_next_tool": "apply_optimization_plan"
        }
