from abc import ABC, abstractmethod
from typing import Dict, Any, List, Generator, Union, Optional 
import json

from llm_services.tool_calling_llm_service import ToolCallingLLMService
from llm_services.summarizer_llm_service import SummarizerLLMService

class BaseAgent(ABC):
    def __init__(self, client, category: str, description: str, manager: Optional[Any] = None):
        self.client = client
        self.category = category
        self.description = description
        self.manager = manager
        
        self.tool_llm_service = ToolCallingLLMService(self.client)
        self.summary_llm_service = SummarizerLLMService(self.client)
        
        self.waiting_for_parameters = False
        self.current_tool_context = None
        self.last_user_request = None
        self.conversation_context = []

    @abstractmethod
    def get_tools(self) -> Dict[str, Any]:
        """Agent'in kullanabileceği araçları döndürür"""
        pass
    
    @abstractmethod
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], original_request: str = None) -> Generator[str, None, None]:
        """Belirtilen aracı çalıştırır"""
        pass
    
    def get_system_prompt(self) -> str:
        """Agent için system prompt oluşturur"""
        tools_description_lines = []
        tools_dict = self.get_tools()

        for name, details in tools_dict.items():
            param_list = []
            for p in details.get("parameters", []):
                param_name = p.get('name', 'param')
                if param_name != "cluster_id":
                    param_list.append(f"{param_name} ({p.get('in', 'N/A')})")

            params_str = ", ".join(param_list) if param_list else "Yok"
            tools_description_lines.append(
                f"  - Arac Adi: '{name}'\n"
                f"  - Aciklama: {details.get('summary', '')}\n"
                f"  - Gerekli Parametreler: {params_str}"
            )
        tools_prompt = "\n".join(tools_description_lines)

        context_info = ""
        if self.conversation_context:
            context_info = f"\n\n### SON SOHBET OZETI ###\n{self._get_conversation_summary()}\n"

        return (
            f"### KİMLİK VE UZMANLIK ALANI ###\n"
            f"Sen, KUBEX platformunda **{self.category}** konusunda uzmanlaşmış bir asistansın. "
            "Temel görevin, kullanıcı taleplerini analiz ederek sahip olduğun araç setini en etkili şekilde kullanmak "
            "ve istenen eylemi başarıyla tamamlamaktır.\n\n"
            f"### ARAÇ SETİ: {self.category} ###\n{tools_prompt}\n"
            f"{context_info}\n"
            "### GÖREV AKIŞI VE KURALLAR ###\n"
            "1. **Talep Analizi:** Kullanıcının talebini dikkatle analiz et. Talebin bir eylem (listeleme, oluşturma, silme vb.) içerip içermediğini belirle.\n"
            "2. **Araç Önceliği:** Eğer kullanıcının talebi, yukarıdaki ARAÇ SETİ'nde listelenen bir aracın açıklamasıyla eşleşiyorsa, o aracı kullanmak **ZORUNLUSUN**.\n"
            "3. **Sohbet İstisnası:** **SADECE** ve **SADECE** taleple eşleşen bir araç yoksa veya kullanıcı genel bir sohbet (selam, nasılsın vb.) başlatıyorsa 'chat' aracını kullan.\n\n"
            "### ÇIKTI FORMATI ###\n"
            "Analizinin sonucunu, **SADECE** aşağıda belirtilen formatta bir JSON objesi olarak döndür. "
            "Yanıtına başka hiçbir metin ekleme.\n\n"
            "1. **Bir Araç Kullanılacaksa:**\n"
            "```json\n"
            "{\n"
            '  "tool_name": "kullanilacak_aracin_adi",\n'
            '  "parameters": {}\n'
            "}\n"
            "```\n\n"
            "2. **Sohbet Yanıtı Verilecekse:**\n"
            "```json\n"
            "{\n"
            '  "tool_name": "chat",\n'
            '  "parameters": {\n'
            '    "response": "Kullanıcıya verilecek net ve yardımcı cevap."\n'
            "  }\n"
            "}\n"
            "```\n\n"
            "### KESİN KURAL ###\n"
            "Kullanıcının talebi bir eylem içeriyorsa ve bu eylem araç setindeki bir araçla yapılabiliyorsa, 'chat' kullanmak **YASAKTIR**. "
            "Doğru aracı seçip JSON çıktısını üret."
        )
    

    def reset_context(self):
        """Bağlamı sıfırla"""
        self.waiting_for_parameters = False
        self.current_tool_context = None
        self.last_user_request = None
    
    def add_to_conversation_context(self, user_message: str, assistant_response: str):
        self.conversation_context.append({
            "user": user_message,
            "assistant": assistant_response,
            "timestamp": "recent"
        })
        
        # Memory limitini koru (son 5 etkileşim)
        if len(self.conversation_context) > 5:
            self.conversation_context = self.conversation_context[-5:]
    
    def _get_conversation_summary(self) -> str:
        if not self.conversation_context:
            return "Henuz bir sohbet gecmisi yok."
            
        summary_parts = []
        for i, interaction in enumerate(self.conversation_context[-3:], 1):  # Son 3 etkileşim
            user_msg = interaction["user"][:100] + "..." if len(interaction["user"]) > 100 else interaction["user"]
            assistant_msg = interaction["assistant"][:100] + "..." if len(interaction["assistant"]) > 100 else interaction["assistant"]
            summary_parts.append(f"{i}. Kullanici: {user_msg}\n   Asistan: {assistant_msg}")
        
        return "\n".join(summary_parts)
    
    def process_request(self, prompt: str) -> Union[Dict[str, Any], Generator[str, None, None]]:        
        self.last_user_request = prompt

        context_reminder = None
        if self.waiting_for_parameters and self.current_tool_context:
            context_reminder = (
                f"BAGLAM: Daha once '{self.current_tool_context['tool_name']}' aracini sectim. "
                f"Eksik parametreler: {', '.join(self.current_tool_context['missing_params'])}. "
                f"ORIJINAL ISTEK: {self.current_tool_context.get('original_request', 'bilinmiyor')}"
            )
        
        llm_decision = self.tool_llm_service.select_tool(
            user_prompt=prompt,
            agent_category=self.category,
            tools=self.get_tools(),
            conversation_summary=self._get_conversation_summary(),
            context_reminder=context_reminder
        )
        
        tool_name = llm_decision.get("tool_name")
        parameters = llm_decision.get("parameters", {})
        
        print(f"[{self.category}] LLM Decision - Tool: {tool_name}, Parameters: {parameters}")
        
        if not tool_name or tool_name == "chat":
            response_text = parameters.get("response", f"{self.category} ile ilgili size nasil yardimci olabilirim?")
            self.waiting_for_parameters = False
            self.current_tool_context = None
            self.add_to_conversation_context(prompt, response_text)
            
            def stream_response():
                yield response_text
            return stream_response()

        tools_dict = self.get_tools()
        tool_info = tools_dict.get(tool_name)
        
        if not tool_info:
            print(f"[{self.category}] LLM var olmayan bir araç seçti: {tool_name}")
            self.waiting_for_parameters = False
            self.current_tool_context = None
            return self._create_error_response(f"'{tool_name}' adinda bir arac bulunamadi.")

        # Geliştirilmiş eksik parametre kontrolü
        missing_params = self._identify_missing_parameters(tool_info, parameters)

        if missing_params:
            print(f"[{self.category}] Eksik parametreler tespit edildi: {missing_params}")
            
            self.waiting_for_parameters = True
            self.current_tool_context = {
                "tool_name": tool_name,
                "missing_params": missing_params,
                "extracted_params": parameters,
                "original_request": prompt
            }
            
            # Kullanıcı dostu sorular oluştur
            user_friendly_questions = self._generate_user_friendly_questions(tool_info, missing_params)
            
            return {
                "status": "needs_parameters",
                "tool_name": tool_name,
                "missing_params": missing_params,
                "questions": user_friendly_questions,
                "extracted_params": parameters
            }

        self.waiting_for_parameters = False
        self.current_tool_context = None
        return self.execute_tool(tool_name, parameters, original_request=prompt)

    def _identify_missing_parameters(self, tool_info: Dict[str, Any], provided_params: Dict[str, Any]) -> List[str]:
        """Eksik parametreleri tespit eder - geliştirilmiş versiyon"""
        missing_params = []
        
        for param_def in tool_info.get("parameters", []):
            param_name = param_def.get("name")
            is_required = param_def.get("required", False)
            
            # cluster_id'yi atla - otomatik olarak enjekte edilir
            if param_name == "cluster_id":
                continue
                
            # Parametre ismi yoksa atla
            if not param_name:
                continue
                
            # Gerekli parametre ve sağlanmamışsa missing listesine ekle
            if is_required and param_name not in provided_params:
                missing_params.append(param_name)
            
            # Sağlanmış ama boş string ise de missing say
            elif param_name in provided_params and not str(provided_params[param_name]).strip():
                missing_params.append(param_name)
        
        return missing_params
    
    def _generate_user_friendly_questions(self, tool_info: Dict[str, Any], missing_params: List[str]) -> List[str]:
        """Eksik parametreler için kullanıcı dostu sorular oluşturur"""
        questions = []
        
        # Parametre bilgilerini bir dict'e dönüştür
        param_info_dict = {p.get("name"): p for p in tool_info.get("parameters", [])}
        
        for param_name in missing_params:
            param_info = param_info_dict.get(param_name, {})
            description = param_info.get("description", "")
            
            # Parametre adına göre özel sorular
            if param_name == "name" or param_name == "deployment_name":
                questions.append(f"Lütfen {param_name} bilgisini girin:")
            elif param_name == "namespace" or param_name == "namespace_name":
                questions.append("Hangi namespace'de işlem yapmak istiyorsunuz?")
            elif param_name == "replicas":
                questions.append("Kaç adet replica istiyorsunuz? (sayı girin)")
            elif param_name == "image":
                questions.append("Yeni container image adını girin (örn: harbor.bulut.ai/app:v1.2):")
            elif param_name == "url":
                questions.append("Repository URL'sini girin:")
            elif param_name == "chart":
                questions.append("Chart adını girin (repo_adı/chart_adı formatında):")
            elif param_name == "values":
                questions.append("Values (JSON formatında, opsiyonel):")
            else:
                # Generic soru
                if description:
                    questions.append(f"{param_name}: {description}")
                else:
                    questions.append(f"Lütfen '{param_name}' değeri için bilgi verin:")
        
        return questions

    def finalize_request(self, tool_name: str, extracted_params: dict, collected_params: dict) -> Generator[str, None, None]:
        """Parametre toplama tamamlandıktan sonra aracı çalıştır - iyileştirilmiş context ile"""
        all_params = {**extracted_params, **collected_params}
        self.waiting_for_parameters = False

        # DEBUG LOGGING
        original_request = "Original request context not found"
        if self.current_tool_context:
            original_request = self.current_tool_context.get("original_request", "Original request key missing")
        
        print(f"[{self.category}] Finalizing tool execution.")
        print(f"[{self.category}] Tool Name: {tool_name}")
        print(f"[{self.category}] All Parameters for execution: {all_params}")
        print(f"[{self.category}] Original Request context: {original_request}")
            
        self.current_tool_context = None
        return self.execute_tool(tool_name, all_params, original_request=original_request)
   
    def _create_error_response(self, error_message: str) -> Generator[str, None, None]:
        """Hata yanıtı oluştur"""
        if self.last_user_request:
            self.add_to_conversation_context(self.last_user_request, error_message)
            
        def stream_response():
            yield error_message
        return stream_response()
    
    def _summarize_result_for_user(self, result: Any, original_request: str = None) -> Generator[str, None, None]:
        if not original_request:
            original_request = self.last_user_request or "Bilinmeyen istek"

        response_generator = self.summary_llm_service.summarize_stream(
            tool_result=result,
            original_request=original_request,
            agent_category=self.category
        )
        
        full_response = "".join(list(response_generator))
            
        if original_request:
            self.add_to_conversation_context(original_request, full_response)
        
        def stream_wrapper():
            yield full_response
        return stream_wrapper()