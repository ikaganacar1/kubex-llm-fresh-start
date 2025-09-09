import logging
import json
import re
from typing import Union, Generator, Dict, Any
from ollama import OllamaClient  # Lütfen dosya adını kendi projenize göre düzeltin
from tools.tool_manager import ToolManager
from tools.cluster_tools import ClusterAPITools

# Logger yapılandırması
logger = logging.getLogger(__name__)

class KubernetesAgent:
    def __init__(self, client: OllamaClient):
        self.client = client
        self.tool_manager = ToolManager()
        self.cluster_api = ClusterAPITools(base_url="http://localhost:8000")
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        # Bu fonksiyonun içeriği doğru ve değiştirilmesine gerek yok.
        tools_description_lines = ["Kullanicinin istegini yerine getirmek icin asagidaki araclardan birini secebilirsin:"]
        tools_dict = self.tool_manager.tools
        for name, details in tools_dict.items():
            param_list = [f"{p.get('name', 'param')} ({p.get('in', 'N/A')})" for p in details.get("parameters", [])]
            params_str = ", ".join(param_list) if param_list else "Yok"
            tools_description_lines.append(
                f"- Arac Adi: '{name}'\n"
                f"  - Aciklama: {details.get('summary', '')}\n"
                f"  - Gerekli Parametreler: {params_str}"
            )
        tools_prompt = "\n".join(tools_description_lines)

        return (
            "Sen KUBEX, bir Kubernetes uzmani asistansin. Gorevin, kullanicinin istegini analiz etmek "
            "ve bu istegi yerine getirmek icin sana verilen araclardan uygun olani secmektir. "
            "Eger kullanicinin istegi bir aracla karsilanamiyorsa, normal bir sohbet yaniti ver.\n\n"
            f"{tools_prompt}\n\n"
            "Kullanicinin istegini analiz ettikten sonra, YALNIZCA bir JSON objesi dondur. "
            "JSON objesi su formatlardan birinde olmalidir:\n\n"
            "1. Arac kullanacaksan, su formati kullan:\n"
            '{"tool_name": "kullanilacak_arac_adi", "parameters": {"parametre_adi": "deger"}}\n\n'
            "2. Sohbet edeceksen, su formati kullan:\n"
            '{"tool_name": "chat", "parameters": {"response": "kullaniciya_verilecek_cevap"}}\n\n'
            "Yanitinda JSON objesi disinda KESINLIKLE hicbir metin, aciklama veya formatlama isareti olmasin."
        )

    def _call_llm_for_tool_selection(self, prompt: str) -> Dict[str, Any]:
        # Bu fonksiyonun içeriği doğru ve değiştirilmesine gerek yok.
        try:
            response = self.client.chat(user_prompt=prompt, system_prompt=self.system_prompt, use_history=False)
            content = response.get("message", {}).get("content", "{}")
            first_brace_index = content.find('{')
            if first_brace_index == -1:
                raise json.JSONDecodeError("Metinde JSON başlangıcı ('{') bulunamadı.", content, 0)
            json_str_with_trailing_junk = content[first_brace_index:]
            decoded_json, _ = json.JSONDecoder().raw_decode(json_str_with_trailing_junk)
            return decoded_json
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"LLM'den gecerli bir JSON alinamadi. Yanit: '{content}'. Hata: {e}")
            return {"tool_name": "chat", "parameters": {"response": "Ne istediginizi anlayamadim, lutfen daha net bir sekilde ifade eder misiniz?"}}

    def process_request(self, prompt: str) -> Union[Dict[str, Any], Generator[str, None, None]]:
        # Bu fonksiyonun içeriği doğru ve değiştirilmesine gerek yok.
        logger.info(f"İstek işleniyor: {prompt}")
        llm_decision = self._call_llm_for_tool_selection(prompt)
        tool_name = llm_decision.get("tool_name")
        parameters = llm_decision.get("parameters", {})

        if not tool_name or tool_name == "chat":
            response_text = parameters.get("response", "Size nasil yardimci olabilirim?")
            def stream_response():
                yield response_text
            return stream_response()

        tool_info = self.tool_manager.get_tool(tool_name)
        if not tool_info:
            logger.warning(f"LLM var olmayan bir araç seçti: {tool_name}")
            return self._summarize_result_for_user(f"'{tool_name}' adinda bir arac bulunamadi.")

        missing_params = []
        for required_param in tool_info.get("parameters", []):
            if required_param.get("required") and required_param.get("name") not in parameters:
                missing_params.append(required_param.get("name"))

        if missing_params:
            logger.info(f"Eksik parametreler tespit edildi: {missing_params}")
            return {
                "status": "needs_parameters",
                "tool_name": tool_name,
                "missing_params": missing_params,
                "questions": [f"Lutfen '{p}' degeri icin bilgi verin:" for p in missing_params],
                "extracted_params": parameters
            }

        return self._execute_tool(tool_name, parameters)

    def finalize_request(self, tool_name: str, extracted_params: dict, collected_params: dict) -> Generator[str, None, None]:
        # Bu fonksiyonun içeriği doğru ve değiştirilmesine gerek yok.
        all_params = {**extracted_params, **collected_params}
        return self._execute_tool(tool_name, all_params)

    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Generator[str, None, None]:
        # Bu fonksiyonun içeriği doğru ve değiştirilmesine gerek yok.
        logger.info(f"Arac calistiriliyor: '{tool_name}', Parametreler: {parameters}")
        tool_function = getattr(self.cluster_api, tool_name, None)
        if not tool_function:
            logger.error(f"'{tool_name}' araci icin 'cluster_tools' icinde eslesen fonksiyon bulunamadi.")
            return self._summarize_result_for_user(f"'{tool_name}' adli aracin calistirma metodu bulunamadi.")
        try:
            result = tool_function(**parameters)
            return self._summarize_result_for_user(result)
        except Exception as e:
            logger.error(f"Arac calistirilirken hata olustu ({tool_name}): {e}")
            return self._summarize_result_for_user({"error": str(e)})

    def _summarize_result_for_user(self, result: Any) -> Generator[str, None, None]:
        # Bu fonksiyonun içeriği doğru ve değiştirilmesine gerek yok.
        summary_prompt = (
            f"Bir arac calistirildi ve sonuc olarak asagidaki JSON verisi alindi. "
            f"Bu sonucu kullanici icin kolay anlasilir, dogal bir dilde (Turkce) ozetle. "
            f"Eger bir hata varsa hatayi belirt. Teknik terimleri basitce acikla.\n\n"
            f"JSON Verisi:\n{json.dumps(result, indent=2, ensure_ascii=False)}\n"
        )
        logger.info("Arac sonucu icin LLM'den ozet isteniyor.")
        return self.client.chat_stream(
            user_prompt=summary_prompt,
            use_history=False
        )

