# llm_services/tool_calling_llm_service.py

import json
from typing import Dict, Any, Optional

class ToolCallingLLMService:
    """
    Bir agent'ın araç setinden kullanıcı talebine en uygun aracı seçmekle sorumlu LLM servisi.
    """
    def __init__(self, client: Any):
        self.client = client

    def _build_system_prompt(self, agent_category: str, tools: Dict[str, Any], conversation_summary: str) -> str:
        """Araç seçimi LLM'i için sistem komutunu oluşturur."""
        tools_description_lines = []
        for name, details in tools.items():
            param_list = [f"{p['name']} ({p.get('in', 'N/A')})" for p in details.get("parameters", []) if p.get('name') != "cluster_id"]
            params_str = ", ".join(param_list) if param_list else "Yok"
            tools_description_lines.append(
                f"  - Arac Adi: '{name}'\n"
                f"  - Aciklama: {details.get('summary', '')}\n"
                f"  - Gerekli Parametreler: {params_str}"
            )
        tools_prompt = "\n".join(tools_description_lines)

        context_info = f"\n\n### SON SOHBET OZETI ###\n{conversation_summary}\n" if conversation_summary else ""

        return (
            f"### KİMLİK VE UZMANLIK ALANI ###\n"
            f"Sen, KUBEX platformunda **{agent_category}** konusunda uzmanlaşmış bir asistansın. "
            "Görevin, kullanıcı talebini analiz ederek sahip olduğun araç setini en etkili şekilde kullanmaktır.\n\n"
            f"### ARAÇ SETİ: {agent_category} ###\n{tools_prompt}\n"
            f"{context_info}\n"
            "### GÖREV AKIŞI VE KURALLAR ###\n"
            "1. **Analiz:** Kullanıcı talebini analiz et.\n"
            "2. **Araç Önceliği:** Talep, ARAÇ SETİ'ndeki bir araçla eşleşiyorsa, o aracı kullanmak **ZORUNLUSUN**.\n"
            "3. **Sohbet İstisnası:** **SADECE** taleple eşleşen bir araç yoksa veya kullanıcı genel bir sohbet başlatıyorsa 'chat' aracını kullan.\n\n"
            "### ÇIKTI FORMATI ###\n"
            "Analizinin sonucunu, **SADECE** belirtilen formatta bir JSON objesi olarak döndür. Başka hiçbir metin ekleme.\n\n"
            "```json\n"
            "{\n"
            '  "tool_name": "kullanilacak_aracin_adi | chat",\n'
            '  "parameters": {}\n'
            "}\n"
            "```\n"
            "### KESİN KURAL ###\n"
            "Kullanıcının talebi bir eylem içeriyorsa ve bu eylem araç setindeki bir araçla yapılabiliyorsa, 'chat' kullanmak **YASAKTIR**."
        )

    def select_tool(self, user_prompt: str, agent_category: str, tools: Dict[str, Any], conversation_summary: str, context_reminder: Optional[str] = None) -> Dict[str, Any]:
        """LLM'den araç seçimi yapmasını ister."""
        system_prompt = self._build_system_prompt(agent_category, tools, conversation_summary)
        
        final_user_prompt = user_prompt
        if context_reminder:
            final_user_prompt = f"{context_reminder}\n\nKullanici mesaji: {user_prompt}"

        print("\n" + "="*50)
        print(f"[{agent_category}] Kullanıcı İsteği: {final_user_prompt}")
        print("="*50 + "\n")

        try:
            response = self.client.chat(
                user_prompt=final_user_prompt, 
                system_prompt=system_prompt, 
                use_history=True
            )
            content = response.get("message", {}).get("content", "{}")
            
            first_brace_index = content.find('{')
            if first_brace_index == -1:
                raise ValueError("JSON bulunamadı")
            
            json_str = content[first_brace_index:]
            decoded_json, _ = json.JSONDecoder().raw_decode(json_str)
            return decoded_json
        except Exception as e:
            print(f"[{agent_category}] LLM'den geçerli JSON alınamadı: {e}")
            return {"tool_name": "chat", "parameters": {"response": "Ne istediğinizi anlayamadım, lütfen daha net bir şekilde ifade eder misiniz?"}}