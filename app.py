import pandas as pd
import pandas_ta as ta
import mplfinance as mpf
from binance.client import Client
from flask import Flask, request, send_file
import io # Untuk menyimpan gambar di memori

# --- Inisialisasi Aplikasi Flask & Klien Binance ---
app = Flask(__name__)
# Untuk data publik seperti Klines (candlestick), kita tidak perlu API key
client = Client()

@app.route('/chart.png')
def plot_chart():
    """
    Endpoint utama untuk membuat dan menampilkan chart.
    Contoh Akses: http://127.0.0.1:5000/chart.png?symbol=BTCUSDT&interval=1h&limit=100
    """
    # --- 1. Ambil Parameter dari URL ---
    # Ambil simbol (misal: BTCUSDT), interval (1m, 5m, 1h, 4h, 1d), dan limit (jumlah lilin)
    symbol = request.args.get('symbol', 'BTCUSDT').upper()
    interval = request.args.get('interval', '1h')
    limit = int(request.args.get('limit', 100))

    try:
        # --- 2. Ambil Data dari Binance ---
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        
        # Jika tidak ada data, kembalikan error (misal: simbol tidak valid)
        if not klines:
            return "Error: Tidak dapat menemukan data untuk simbol atau interval yang diberikan.", 404

        # --- 3. Proses Data menjadi DataFrame yang Cantik ---
        # Buat DataFrame dari data mentah Binance
        df = pd.DataFrame(klines, columns=[
            'Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time', 
            'Quote asset volume', 'Number of trades', 'Taker buy base asset volume', 
            'Taker buy quote asset volume', 'Ignore'
        ])
        
        # Ubah tipe data kolom harga & volume menjadi angka (float)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = pd.to_numeric(df[col])
            
        # Konversi 'Open time' menjadi format tanggal yang bisa dibaca dan jadikan index
        df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
        df.set_index('Open time', inplace=True)

        # --- 4. Hitung Indikator Teknikal dengan pandas-ta ---
        # Ini bagian paling serunya! Kita bisa tambahkan apa saja.
        
        # Relative Strength Index (RSI)
        df.ta.rsi(length=14, append=True)
        
        # Moving Average Convergence Divergence (MACD)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        
        # Bollinger Bands (BBands)
        df.ta.bbands(length=20, std=2, append=True)

        # --- 5. Siapkan Panel-panel untuk Chart ---
        # mplfinance butuh daftar 'addplot' untuk menampilkan indikator di panel terpisah
        
        # Panel 1: RSI di bawah chart utama
        panel_rsi = mpf.make_addplot(df['RSI_14'], panel=1, color='purple', title='RSI(14)')
        
        # Panel 2: MACD di panel paling bawah
        # Kita akan plot histogram, garis macd, dan garis sinyalnya
        panel_macd_hist = mpf.make_addplot(df['MACDh_12_26_9'], type='bar', color='gray', panel=2)
        panel_macd_line = mpf.make_addplot(df['MACD_12_26_9'], color='blue', panel=2, title='MACD')
        panel_macd_signal = mpf.make_addplot(df['MACDs_12_26_9'], color='orange', panel=2)
        
        # Gabungkan semua addplot menjadi satu list
        addplots = [panel_rsi, panel_macd_hist, panel_macd_line, panel_macd_signal]

        # --- 6. Gambar Chart-nya! ---
        # Simpan gambar ke buffer memori, bukan ke file fisik
        buf = io.BytesIO()
        
        # Bollinger Bands akan otomatis ter-plot di chart utama karena namanya sudah standar (BBU, BBL)
        mpf.plot(
            df,
            type='candle',         # Tipe chart candlestick
            style='charles',       # Gaya chart, coba juga 'yahoo' atau 'binance'
            title=f'{symbol} - {interval} Chart',
            ylabel='Harga (USDT)',
            volume=True,           # Tampilkan volume di panel bawah
            ylabel_lower='Volume',
            addplot=addplots,      # Tambahkan panel indikator kita
            panel_ratios=(3, 1, 1), # Rasio ukuran: (chart utama, panel 1, panel 2)
            figscale=1.5,          # Ukuran gambar
            savefig=dict(fname=buf, format='png', dpi=100) # Simpan ke buffer
        )
        
        buf.seek(0) # Pindahkan pointer ke awal buffer
        
        # --- 7. Kirim Gambar sebagai Respons API ---
        return send_file(buf, mimetype='image/png')

    except Exception as e:
        # Tangani jika ada error (misal: koneksi internet, dll)
        return f"Terjadi kesalahan: {e}", 500

if __name__ == '__main__':
    # Jalankan server Flask di mode debug
    app.run(debug=True, host='0.0.0.0', port=5000)
