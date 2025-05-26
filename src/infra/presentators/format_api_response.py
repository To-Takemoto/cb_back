def flatten_api_response(llm_response) -> dict:
    """
    OpenAI APIのレスポンスJSONを、Peeweeの`LLMDetails`モデルに適合する形式に変換する関数
    
    Args:
        llm_response: OpenAI APIからのレスポンスJSON
        message_id: 関連するMessageモデルのID (存在する場合)
    
    Returns:
        LLMDetailsモデルに適合するディクショナリ
        
    Raises:
        ValueError: 入力データが不正な形式の場合
        TypeError: 入力データの型が不正な場合
    """
    # 入力検証
    if not isinstance(llm_response, dict):
        raise TypeError("入力はJSONオブジェクト（辞書型）である必要があります")
    
    # 必須フィールドの確認
    required_fields = ['id', 'provider', 'object', 'created', 'choices', 'usage']
    for field in required_fields:
        if field not in llm_response:
            raise ValueError(f"必須フィールド '{field}' が見つかりません")
    
    # choicesの検証
    if not isinstance(llm_response['choices'], list) or len(llm_response['choices']) == 0:
        raise ValueError("'choices' フィールドは少なくとも1つの要素を持つリストである必要があります")
    
    # 最初のchoiceを使用（一般的に1つしかないため）
    choice:dict = llm_response['choices'][0]
    
    # 必要なフィールドの抽出
    try:
        llm_details_data = {
            'content': choice.get('message', {}).get('content', ''),
            'gen_id': llm_response.get('id', ''),
            'provider': llm_response.get('provider', ''),
            'object_': llm_response.get('object', ''),
            'created': str(llm_response.get('created', '')),
            'finish_reason': choice.get('finish_reason', ''),
            'index_': str(choice.get('index', 0)),
            'message_role': choice.get('message', {}).get('role', ''),
            'prompt_tokens': llm_response.get('usage', {}).get('prompt_tokens', 0),
            'completion_tokens': llm_response.get('usage', {}).get('completion_tokens', 0),
            'total_tokens': llm_response.get('usage', {}).get('total_tokens', 0)
        }
        #print(llm_details_data)
                
        return llm_details_data
        
    except Exception as e:
        raise ValueError(f"JSONデータの処理中にエラーが発生しました: {str(e)}")