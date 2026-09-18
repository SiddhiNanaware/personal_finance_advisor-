import os
import sys
from dotenv import load_dotenv
from pyngrok import ngrok, conf
from app import create_app

# Load environment variables
load_dotenv()

app = create_app()

def main():
    port = int(os.environ.get('PORT', 5000))
    authtoken = os.environ.get('NGROK_AUTHTOKEN', '').strip()

    # Set auth token if provided in .env
    if authtoken:
        ngrok.set_auth_token(authtoken)

    print("=" * 65)
    print(" 🚀 STARTING PERSONAL FINANCE ADVISOR BOT WITH NGROK TUNNEL")
    print("=" * 65)

    try:
        # Establish ngrok tunnel to localhost:5000
        tunnel = ngrok.connect(port, bind_tls=True)
        public_url = tunnel.public_url
        print(f"\n * Local Server:   http://127.0.0.1:{port}")
        print(f" * Public Ngrok URL: {public_url}")
        print(f" * Web Dashboard:  http://127.0.0.1:4040\n")
        print("Share the Public Ngrok URL with evaluators, peers, or users!")
        print("Press CTRL+C to terminate both server and ngrok tunnel.\n")
        print("=" * 65)
    except Exception as e:
        print("\n❌ NGROK ERROR:")
        print(f"   {e}")
        print("\n💡 Tip: Add your ngrok token to your .env file:")
        print("   NGROK_AUTHTOKEN=your_token_here")
        print("   Get a free token from: https://dashboard.ngrok.com/get-started/your-authtoken")
        print("=" * 65)
        sys.exit(1)

    # Start Flask dev server
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
