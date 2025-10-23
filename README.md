WallAudio 噪音蒐證工具
=====================

緣起於樓下鄰居每天清晨四五點會狂敲牆壁把大家嚇醒，警察建議要錄音蒐證，於是有了一連串的行動，包括這套蒐證程式

至於為何叫 WallAudio？這是 ChatGPT 取的名稱，我也沒意見

安裝使用
--------

### 準備 USB 麥克風

我是買 audio-technica ATR2500x-USB 電容式麥克風。

USB 線長度不夠時，可用「主動式USB延長線」，於遠端端口接入直流電源，可為訊號增益。我是在光華商場六樓買到三公尺的，網路上也買得到。

插上 USB 麥克風後，檢查 Windows -> 設定 -> 系統 -> 音效 -> 輸入，應該可以看到此麥克風裝置。

### 下載 ffmpeg.exe

[下載錄音程式 ffmpeg](https://www.ffmpeg.org/download.html)，有選擇困難的人可以選 BtbN 版

設定 PATH 使得於 PowerShell 中執行 `ffmpeg` 命令能正確啟動

註：開始 -> 設定 -> 系統 -> 系統資訊 -> (在相關連結區) 進階系統設定 -> 進階 -> 環境變數

### 複製本專案

    git clone https://github.com/jihghong/WallAudio

以下假設本專案複製到 `C:\Projects\WallAudio` 且錄音檔將存放在 `C:\WallAudio` 子目錄

### 設環境變數 AUDIO_DEV

開啟 PowerShell 視窗，用以下命令找到 USB 麥克風的 ID

    ffmpeg -list_devices true -f dshow -i dummy

找到類似以下訊息

    [dshow @ 000002491b4ca168] "麥克風 (ATR2500x-USB Microphone)" (audio)
    [dshow @ 000002491b4ca168]   Alternative name "@device_cm_{12D9A762-90C8-11D0-BD43-00A0C911CE68}\wave_{785D73F3-069C-4C3D-83CB-A28D2A99D286}"

將環境變數 AUDIO_DEV 設定為以下字串，注意前方要加 `audio=`

    audio=麥克風 (ATR2500x-USB Microphone)

可用以下 setx 指令設定，或進入上述「進階系統設定」操作介面設定

    setx AUDIO_DEV "audio=麥克風 (ATR2500x-USB Microphone)"

注意：環境變數在後續開啟的視窗中才會生效

### 初步測試

執行看看錄音程式

    .\record.ps1

    按 q 離開

結果會將錄音結果產生在 `\WallAudio\YYYY-MM-DD` 子目錄

### 改變錄音模式

若需要改變錄音模式，請直接修改 record.ps1，可能包括

* 啟動 ffmpeg 的方式，例如想改用 `C:\Download\ffmpeg\ffmpeg` 啟動，可修改 $ffmpeg 變數

* 存放錄音結果的子目錄，可修改 $outdir

* 目前設定每日 6:59 結束程式，可修改 $stopTime 來改變

* 目前錄音品質為 -ac 1 單聲道，以 -c:a aac 即 *.m4a 格式儲存，可直接修改程式中 ffmpeg 的參數來改變

* 目前 -segment_time 3600 會每 60 分鐘自動分段錄音，且 -segment_atclocktime 1 會在每小時的整點分段

### 建立工作排程

啟動 Windows 工作排程器，建立基本工作

* 觸發程序：每天 7:00。因程式中有設定隔天 6:59 會關閉，因此每天會有一分鐘錄不到

* 動作：啟動程式設 `powershell`，引數設 `-F record.ps1`，開始位置設 record.ps1 所在的子目錄，例如 `C:\Projects\WallAudio`
