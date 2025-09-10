# llm_services/router_llm_service.py

import json
from typing import Dict, Any

class RouterLLMService:
    """
    Kullanıcı talebini analiz ederek en uygun agent'ı seçmekle sorumlu LLM servisi.
    """
    def __init__(self, client: Any):
        self.client = client
        self.system_prompt = ""

    def _build_system_prompt(self, agents: Dict[str, Any], context_summary: str) -> str:
        """Router LLM için sistem komutunu dinamik olarak oluşturur."""
        agent_descriptions = [
            f"- {key}: {agent.category} - {agent.description}" 
            for key, agent in agents.items()
        ]
        agents_text = "\n".join(agent_descriptions)

        context_info = f"\n\n### SON SOHBET OZETI ###\n{context_summary}\n" if context_summary else ""

        return (
            "### GÖREV VE KİMLİK ###\n"
            "Sen, KUBEX Kubernetes Yönetim Platformu'nun ana yönlendiricisi olan bir \"Triage Uzmanı\"sın. "
            "Temel görevin, kullanıcıdan gelen talebi derinlemesine analiz ederek, bu talebi en doğru şekilde karşılayacak "
            "uzmanlık alanını (agent) belirlemektir.\n\n"
            f"### UZMANLIK ALANLARI (AGENT'LAR) ###\n{agents_text}\n"
            f"{context_info}"
            "### KARAR VERME SÜRECİ ###\n"
            "1. **Amacı Anlama:** Kullanıcının talebini incele (listeleme, oluşturma, silme, genel sohbet vb.).\n"
            "2. **Kaynak Türü:** Talebin merkezindeki kaynağı belirle (Cluster, Deployment, Namespace vb.).\n"
            "3. **Bağlamı Değerlendirme:** Sohbet geçmişini kullanarak kullanıcının bir önceki adıma devam edip etmediğini anla.\n\n"
            "### ÇIKTI FORMATI ###\n"
            "Kararını ve mantığını (`reasoning`) içeren, **SADECE** aşağıdaki formatta bir JSON objesi döndür. "
            "Yanıtına başka hiçbir metin ekleme.\n\n"
            "```json\n"
            "{\n"
            '  "agent": "ilgili_agent_adi | chat",\n'
            '  "reasoning": "Kararın arkasındaki kısa mantık.",\n'
            '  "response": "Eğer agent \'chat\' ise, kullanıcıya verilecek sohbet cevabı."\n'
            "}\n"
            "```"
        )

    def get_routing_decision(self, user_prompt: str, agents: Dict[str, Any], context_summary: str) -> Dict[str, Any]:
        """LLM'den agent yönlendirme kararını alır."""
        system_prompt = self._build_system_prompt(agents, context_summary)
        try:
            response = self.client.chat(
                user_prompt=user_prompt, 
                system_prompt=system_prompt, 
                use_history=True
            )
            content = response.get("message", {}).get("content", "{}")
            
            first_brace_index = content.find('{')
            if first_brace_index == -1:
                raise ValueError("Yanıt içinde JSON objesi bulunamadı.")
            
            json_str = content[first_brace_index:]
            decoded_json, _ = json.JSONDecoder().raw_decode(json_str)
            return decoded_json
            
        except Exception as e:
            print(f"[RouterLLMService] LLM'den geçerli yanıt alınamadı: {e}")
            return {
                "agent": "chat", 
                "reasoning": "Routing sırasında bir hata oluştu.",
                "response": "İsteğinizi şu anda işleyemiyorum, lütfen daha net bir şekilde tekrar dener misiniz?"
            }