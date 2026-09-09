import src.rag_pipeline
from src.prompts import FALLBACK_RESPONSE

def main():
    print("=" * 60)
    print("  URBANSTYLE CHILE - Chatbot de Atención al Cliente")
    print("  Escribe 'salir' para terminar la conversación")
    print("=" * 60)
    print("\nInicializando pipeline RAG...")
    chain = src.rag_pipeline.create_rag_chain()
    print("Listo. Puedes hacer tu consulta.\n")

    while True:
        user_input = input("Tú: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("salir", "exit", "quit"):
            print("\nGracias por contactar UrbanStyle. ¡Hasta pronto!")
            break

        try:
            result = src.rag_pipeline.query(chain, user_input)
            print(f"\nUrbanBot: {result['answer']}")
            if result["sources"]:
                print(f"  [Fuentes: {', '.join(result['sources'])}]")
        except Exception as e:
            print(f"\nUrbanBot: {FALLBACK_RESPONSE}")
            print(f"  [Error técnico: {e}]")
        print()


if __name__ == "__main__":
    main()
