import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import tkinter.scrolledtext as tkst
import tkinter.ttk as ttk
import os
import pandas as pd
import time
import re
import matplotlib
import matplotlib.pyplot as plt

plt.style.use('ggplot')
font = {'family': 'meiryo'}
matplotlib.rc('font', **font)

# 集計単位の選択肢
MEAN_TIMES = {
    '生データ': 'org',
    '1分平均': '1T',
    '2分平均': '2T',
    '5分平均': '5T',
    '10分平均': '10T',
    '15分平均': '15T',
    '30分平均': '30T',
    '1時間平均': '1H',
    '3時間平均': '3H',
    '6時間平均': '6H',
    '12時間平均': '12H',
    '1日平均': '1D',
}


# ==============================
# LabelFrame
# ==============================
class MyLabelFrame(tk.LabelFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(
            master=master,
            padx=4,
            labelanchor=tk.NW,
            foreground='blue',
        )
        self.config(**kwargs)  # 指定オプションの設定

    def grid(self, **kwargs):
        super().grid(
            sticky=(tk.N, tk.S, tk.E, tk.W),
            ipady=2,
            padx=2,
            pady=2,
            **kwargs,
        )


# ==============================
# Combobox（リスト）
# ==============================
class MyCombobox(ttk.Combobox):
    def __init__(self, master=None, **kwargs):
        super().__init__(
            master=master,
            width=12,
            state='readonly',
        )
        self.config(**kwargs)  # 指定オプションの設定


# ==============================
# Spinbox（増減ボタンありのEntry）
# ==============================
class MySpinbox(ttk.Spinbox):
    def __init__(self, master=None, **kwargs):
        super().__init__(
            master=master,
            width=12,
        )
        self.config(**kwargs)  # 指定オプションの設定


# ==============================
# ScrolledText
# ==============================
class MyScrolledText(tkst.ScrolledText):
    def __init__(self, master=None, **kwargs):
        super().__init__(
            master=master,
            width=100,
            state='disabled',
        )
        self.config(**kwargs)  # 指定オプションの設定

    def grid(self, **kwargs):
        super().grid(
            sticky=(tk.N, tk.S, tk.E, tk.W),
            ipady=2,
            padx=2,
            pady=2,
            **kwargs,
        )

    def write(self, text):
        self['state'] = 'normal'
        self.insert('end', text)
        self['state'] = 'disabled'
        self.see('end')


# ============================================================
class InformationFrame(MyLabelFrame):
    '''情報表示用フレーム
    '''
    def __init__(self, master=None, **kwargs):
        self.widget = []
        super().__init__(master, **kwargs)

    def write(self, msg):
        '''リスト msg の内容を新しいLabelを作成して配置する
        '''
        # 古いラベルを削除する
        [w.destroy() for w in self.widget]
        # 新しいラベルを作成
        self.widget = [tk.Label(self, text=s, anchor=tk.W) for s in msg]
        [w.pack(fill=tk.X) for w in self.widget]


# ============================================================
class SelectMeanTimeFrame(MyLabelFrame):
    '''集計単位の選択フレーム
    '''
    def __init__(self, master=None, **kwargs):
        global var_mean_time
        self.var_mean_time = var_mean_time
        super().__init__(master, text='集計単位', **kwargs)
        self.cb = MyCombobox(
            master=self,
            values=list(MEAN_TIMES.keys()),
            textvariable=self.var_mean_time,
        )
        self.cb.current(3)         # 初期値を設定
        self.cb.grid(row=0, column=0)


# ============================================================
class SelectOutputPeriodFrame(MyLabelFrame):
    '''グラフ出力の対象期間（日付）の選択フレーム
    '''
    def __init__(self, dates=None, master=None, **kwargs):
        global var_from, var_to
        self.var_from = var_from
        self.var_to = var_to
        super().__init__(master, text='対象期間', **kwargs)

        # 開始日
        self.cb_from = MyCombobox(
            master=self, textvariable=self.var_from, state='disable',
        )
        self.cb_from.bind('<<ComboboxSelected>>', self.check_var_to)
        self.cb_from.bind('<MouseWheel>', self.check_var_to)
        self.cb_from.grid(row=0, column=0)

        # 終了日
        self.cb_to = MyCombobox(
            master=self, textvariable=self.var_to, state='disable',
        )
        self.cb_to.bind('<<ComboboxSelected>>', self.check_var_from)
        self.cb_to.bind('<MouseWheel>', self.check_var_from)
        self.cb_to.grid(row=0, column=2)

        # 間の '～'
        tk.Label(master=self, text='～').grid(row=0, column=1)

        # 日付の選択肢のセット
        if dates is not None:
            self.set_values(dates)

    def set_values(self, dates):
        self.cb_from['values'] = [str(d) for d in dates]
        self.cb_from['state'] = 'normal'
        self.cb_from.current(0)  # 初期値を設定

        self.cb_to['values'] = [str(d) for d in dates]
        self.cb_to['state'] = 'normal'
        self.cb_to.current(len(dates)-1)  # 初期値を設定

    # from の日付が to を超えたら to の値を修正する
    def check_var_to(self, event=None):
        if self.var_from.get() > self.var_to.get():
            self.var_to.set(self.var_from.get())

    # to の日付が from を下回ったら from の値を修正する
    def check_var_from(self, event=None):
        if self.var_from.get() > self.var_to.get():
            self.var_from.set(self.var_to.get())


class SelectAxisScaleFrame(MyLabelFrame):
    '''縦軸のスケールを指定するフレーム'''
    def __init__(self, master=None, **kwargs):
        global var_axis_unit, var_axis_type, var_axis_value
        self.var_axis_unit = var_axis_unit
        self.var_axis_type = var_axis_type
        self.var_axis_value = var_axis_value
        # 縦軸のスケールの辞書
        self.AXIS_VALUES = {}
        self.AXIS_VALUES.update({'{} Mbps'.format(i): int(i*1e6) for i in range(1, 10, 1)})
        self.AXIS_VALUES.update({'{} Mbps'.format(i): int(i*1e6) for i in range(10, 100, 10)})
        self.AXIS_VALUES.update({'{} Mbps'.format(i): int(i*1e6) for i in range(100, 1000, 100)})
        self.AXIS_VALUES.update({'{} Gbps'.format(i): int(i*1e9) for i in range(1, 11, 1)})
        # 縦軸の単位とspinboxの増分の辞書
        self.AXIS_UNITS = {
            'bps': int(1e3),
            'kbps': int(100e3),
            'Mbps': int(1e6),
            'Gbps': int(1e6),
        }

        super().__init__(master, text='縦軸の設定', **kwargs)

        # 子フレーム：単位 ====================
        lf = MyLabelFrame(self, text='単位')
        lf.pack(anchor=tk.W, fill=tk.X)
        for text in self.AXIS_UNITS.keys():
            tk.Radiobutton(
                master=lf, text=text, value=text, variable=self.var_axis_unit,
                command=self.set_increment
            ).pack(anchor=tk.W, side=tk.LEFT)

        # 子フレーム：スケール ====================
        lf = MyLabelFrame(self, text='スケール')
        lf.pack(anchor=tk.W, fill=tk.X)

        # 1列目、自動 or 固定 or 指定のラジオボタン
        for row, (text, value) in enumerate([['自動', 'auto'], ['固定', 'fix'], ['指定', 'specified']]):
            tk.Radiobutton(
                master=lf, text=text, value=value, variable=self.var_axis_type,
                command=self.change_state
            ).grid(row=row, column=0, sticky=tk.NW)

        # 1行/2列目、固定値の選択リスト
        self.cb = MyCombobox(
            master=lf,
            values=list(self.AXIS_VALUES.keys()),
            state='disable',
        )
        self.cb.current(9)  # 初期値を指定
        self.cb.bind('<<ComboboxSelected>>', self.set_var_axis_value)
        self.cb.bind('<MouseWheel>', self.set_var_axis_value)
        self.cb.grid(row=1, column=1, sticky=tk.W)

        # 2行/2列目、指定値の入力欄
        self.sb = MySpinbox(
            master=lf, from_=1, to=10e9, increment=1000,
            textvariable=self.var_axis_value,
            command=self.spin_changed,
            state='disable',
        )
        self.sb.bind('<MouseWheel>', self.wheel)
        self.sb.grid(row=2, column=1, sticky=tk.W)
        tk.Label(lf, text='bps').grid(row=2, column=2)  # 単位を表示

        # 固定値の初期値に合わせて値を設定
        self.set_var_axis_value()

    def wheel(self, event):
        increment = int(self.sb.config('increment')[-1])  # incrementの現在値を抽出
        value = self.var_axis_value.get()
        if (event.delta > 0):  # 上向きホイール
            value += increment
        elif (event.delta < 0):  # 下向きホイール
            value -= increment
        if value <= 0:
            value = increment
        self.var_axis_value.set(value)

    def set_var_axis_value(self, event=None):
        self.var_axis_value.set(self.AXIS_VALUES[self.cb.get()])

    # spinboxのボタンが押されたときに値をチェック
    def spin_changed(self):
        try:
            self.var_axis_value.get()
        except Exception:
            self.var_axis_value.set(1)
        if self.var_axis_value.get() < 1:  # 0より下の値を入力した時、1にする
            self.var_axis_value.set(1)

    # spinboxの増分を設定
    def set_increment(self):
        self.sb['increment'] = self.AXIS_UNITS[self.var_axis_unit.get()]

    # チェックボックスに合わせて他のウィジェットのstateを変更する
    def change_state(self):
        if self.var_axis_type.get() == 'fix':
            self.cb['state'] = 'readonly'   # cb有効
            self.sb['state'] = 'disable'    # sb無効
            self.set_var_axis_value()
        elif self.var_axis_type.get() == 'specified':
            self.cb['state'] = 'disable'    # cb無効
            self.sb['state'] = 'normal'     # sb有効
        else:
            self.cb['state'] = 'disable'
            self.sb['state'] = 'disable'


class ButtonFrame(tk.Frame):
    def __init__(self, target, file_info, period, msg, master=None, **kwargs):
        global var_mean_time, var_axis_unit, var_from, var_to
        self.var_mean_time = var_mean_time
        self.var_axis_unit = var_axis_unit
        self.var_from = var_from
        self.var_to = var_to
        self.TargetFrame = target
        self.FileInfoFrame = file_info
        self.PeriodFrame = period
        self.MsgFrame = msg  # メッセージフレーム
        self.csv_data = pd.DataFrame()
        super().__init__(master=master)
        # 読込ボタン
        self.ReadButton = tk.Button(
            self,
            text='ファイル読込',
            width=len('ファイル読込') * 2,
            command=self.read_stg_thread,
        )
        self.ReadButton.pack(side=tk.LEFT, padx=2, pady=2)
        # 実行ボタン
        self.DrawButton = tk.Button(
            self,
            text='グラフ表示',
            width=len('グラフ表示') * 2,
            command=self.output_graph,
            state='disable',
        )
        self.DrawButton.pack(side=tk.LEFT, padx=2, pady=2)
        # 終了ボタン
        self.QuitButton = tk.Button(
            self,
            text='終了',
            command=self.abort
        )
        self.QuitButton.pack(side=tk.LEFT, padx=2, pady=2)

    def abort(self):
        plt.close('all')
        root.destroy()

    def read_stg_thread(self):
        import threading
        th = threading.Thread(target=self.read_stg, args=())
        th.start()

    def read_stg(self):
        # ファイルダイアログを開く
        filetypes = [('STGローテーションファイル', '*.csv;*.csv.*'), ('すべて', '*'), ]
        csv_filenames = filedialog.askopenfilenames(filetypes=filetypes, initialdir='.')
        # ファイル指定がなければ終了
        if csv_filenames == '':
            return

        # CSVファイルのチェック
        for idx, filename in enumerate(csv_filenames):
            line = ''
            # ファイルを開いて1行読み込み
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    line = f.readline().rstrip()  # 1行読み込み
            except UnicodeDecodeError as err:
                self.MsgFrame.write('Error!：文字コードエラー\n  {}\n'.format(filename))
                messagebox.showerror('文字コードエラー', '文字コードがUTF-8ではありません\n{}\n{}'.format(filename, err))
                return
            except Exception as other:
                self.MsgFrame.write('Error!：ファイルオープンエラー\n  {}\n'.format(filename))
                messagebox.showerror('ファイルオープンエラー', 'ファイルが開けません\n{}\n{}'.format(filename, other))
                return

            # チェック１：STGのファイルであることのチェック
            # 　　　　　　行頭がSTGでカンマ区切りで5カラムあること
            columns = re.split(',', line)
            if len(line) < 3 or line[:3] != 'STG' or len(columns) != 5:
                self.MsgFrame.write('Error!：ファイルフォーマットエラー\n  {}\n'.format(filename))
                messagebox.showerror(
                    'ファイルフォーマットエラー',
                    'STGのCSVファイルではありません\n{}'.format(filename)
                )
                return
            # ターゲットアドレスを取得
            m = re.match('Target Address:(.+)', columns[1])
            if not m:
                self.MsgFrame.write('Error!：ファイルフォーマットエラー\n  {}\n'.format(filename))
                messagebox.showerror(
                    'ファイルフォーマットエラー',
                    'STGのCSVファイルではありません\n{}'.format(filename)
                )
                return
            self.target_ip = m.group(1)

            # チェック２：Target情報が前に読み込んだファイルと一致するかチェック
            if idx == 0:  # ファイル1個目
                target = columns[1:]
            elif target != columns[1:]:
                self.MsgFrame.write('Error!：ファイル指定エラー\n  {}\n'.format(filename))
                messagebox.showerror(
                    'ファイル指定エラー',
                    '{} の対象情報が一致しません'.format(os.path.basename(filename))
                )
                return

        # CSVファイルの読込
        self.ReadButton['state'] = 'disable'  # ReadButtonをロック
        self.DrawButton['state'] = 'disable'  # DrawButtonをロック
        t = ExecTime()
        import datetime
        self.MsgFrame.write(
            '{} ファイル読込開始（{} files）\n'.format(
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                len(csv_filenames))
        )
        for idx, filename in enumerate(csv_filenames):
            self.MsgFrame.write(
                ' [{}/{}]：{} ... '.format(idx+1, len(csv_filenames), filename),
            )
            df = pd.read_csv(
                filename,
                encoding='SHIFT-JIS',                       # 文字コードを指定
                header=1,                                   # 0行目（最初の行）を読み飛ばす
                names=['date', 'uptime', 'recv', 'send'],   # カラム名を設定
            )
            # STGのバグ対応、AugがAvgになっているので置換
            df['date'] = pd.to_datetime(df['date'].str.replace('Avg', 'Aug'))
            df.set_index('date', inplace=True)
            if idx == 0:  # ファイル1個目
                self.csv_data = df
            else:        # ファイル2個目以降
                self.csv_data = pd.concat([self.csv_data, df])

            self.MsgFrame.write(
                '{:.3f} sec\n'.format(t.laptime)
            )
        # カレントディレクトの変更
        os.chdir(os.path.dirname(csv_filenames[0]))
        self.MsgFrame.write(' 出力先：{}\n'.format(os.getcwd()))
        self.MsgFrame.write(
            '{} 読込完了\n'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        self.csv_data.drop_duplicates(inplace=True)                     # 重複行を削除する
        self.csv_data = self.csv_data.sort_index()                      # インデックス順（日時）でソートする
        self.csv_data = self.csv_data.query('uptime != 0')              # uptimeが0の行を削除する
        self.csv_data['delta_time'] = self.csv_data['uptime'].diff()    # delta_timeを計算する。
        self.csv_data.drop('uptime', axis=1, inplace=True)              # uptimeを削除する

        # 機器情報出力
        self.TargetFrame.write(target)
        # ファイル情報出力
        recv = self.csv_data['recv'] * 8 * 100 // self.csv_data['delta_time']
        send = self.csv_data['send'] * 8 * 100 // self.csv_data['delta_time']
        delta = self.csv_data['delta_time'] / 100
        text = [
            '開始日時: {}'.format(str(self.csv_data.index[0])[:-7]),
            '終了日時: {}'.format(str(self.csv_data.index[-1])[:-7]),
            '取得間隔: {:,} ～ {:,} 秒'.format(delta.min(), delta.max()),
            '取得行数: {:,}'.format(self.csv_data.shape[0]),
            '受信帯域: 最大 {:,} bps'.format(int(recv.max())),
            '送信帯域: 最大 {:,} bps'.format(int(send.max())),
        ]
        self.FileInfoFrame.write(text)
        # 期間情報設定
        self.PeriodFrame.set_values(sorted(set(self.csv_data.index.date)))

        self.ReadButton['state'] = 'normal'  # ReadButtonをロック解除
        self.DrawButton['state'] = 'normal'  # DrawButtonをロック解除

    def output_graph(self):
        '''
        指定の時間でスループットを計算してCSVに吐き出す
        グラフも表示する。
        '''
        rule = MEAN_TIMES[self.var_mean_time.get()]
        axis_unit = self.var_axis_unit.get()

        # 指定時間で集約
        if rule == 'org':
            df = self.csv_data.copy()
        else:
            df = self.csv_data.resample(rule=rule).sum()

        # 指定期間を抽出
        df = df[self.var_from.get():self.var_to.get()]

        # スループットを計算
        if axis_unit == 'bps':
            div_unit = 1
        elif axis_unit == 'kbps':
            div_unit = int(1e3)
        elif axis_unit == 'Mbps':
            div_unit = int(1e6)
        elif axis_unit == 'Gbps':
            div_unit = int(1e9)

        recv_unit = 'recv_' + axis_unit
        send_unit = 'send_' + axis_unit
        df[recv_unit] = df['recv'] * 8 * 100 // df['delta_time'] / div_unit
        df[send_unit] = df['send'] * 8 * 100 // df['delta_time'] / div_unit

        # CSVファイル出力
        output_columns = ['delta_time', recv_unit, send_unit]
        df[output_columns].to_csv('{}_{}.csv'.format(self.target_ip, var_mean_time.get()), sep=',')

        # 送受信の最大値と発生日時を調べる
        recv_max = df[recv_unit].max()
        send_max = df[send_unit].max()
        recv_max_date = re.sub(r'\.\d+$', '', str(df[df[recv_unit] == recv_max].index.tolist()[0]))
        send_max_date = re.sub(r'\.\d+$', '', str(df[df[send_unit] == send_max].index.tolist()[0]))

        # 送受信の最大値の文字列を作成、MbpsとGbpsは少数点3桁表示
        if axis_unit == 'Mbps' or axis_unit == 'Gbps':
            recv_max_str = '{:,.3f}'.format(recv_max)
            send_max_str = '{:,.3f}'.format(send_max)
        else:
            recv_max_str = '{:,}'.format(int(recv_max))
            send_max_str = '{:,}'.format(int(send_max))

        strlen_max = max(len(recv_max_str), len(send_max_str))

        str1 = '受信MAX: {max:>{len}} {unit} ({date})'.format(
            max=recv_max_str,
            date=recv_max_date,
            unit=axis_unit,
            len=strlen_max,
        )
        str2 = '送信MAX: {max:>{len}} {unit} ({date})'.format(
            max=send_max_str,
            date=send_max_date,
            unit=axis_unit,
            len=strlen_max,
        )

        # グラフ描画
        ax = df.plot(
            grid=True,
            y=[recv_unit, send_unit],
            title='{} スループット（{}）'.format(self.target_ip, var_mean_time.get())
            )
        # X軸ラベル
        ax.set_xlabel('日時')
        # Y軸ラベル
        ax.set_ylabel(axis_unit)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: '{:,.1f}'.format(x)))
        ax.grid(which='major', color='gray', linestyle='--')
        ax.grid(which='minor', color='gray', linestyle='--')
        # Y軸のスケール
        if var_axis_type.get() == 'auto':
            ax.set_ylim(0,)
        else:
            ax.set_ylim([0, var_axis_value.get() // div_unit])

        # 送受信の最大値をグラフ上にテキスト表示
        ax.text(0.05, 0.9, str1 + '\n' + str2, family='ms gothic', transform=ax.transAxes)

        plt.show()


# =================================================================
class ExecTime():
    '''コマンドの実行時間を測定する'''
    def __init__(self, init_time=0):
        self.t1 = time.time() if init_time == 0 else init_time

    @property
    def laptime(self):
        t2 = time.time()
        result = t2 - self.t1
        self.t1 = t2
        return result

    @property
    def print(self):
        print('{:.3f} sec'.format(self.laptime))


# =================================================================
# メインルーチン
# =================================================================
if __name__ == '__main__':
    root = tk.Tk()
    root.withdraw()

    # ウィジェット共通の変数
    var_axis_unit = tk.StringVar(value='kbps')  # 縦軸の単位 bps / kbps / Mbps
    var_axis_type = tk.StringVar(value='auto')  # 縦軸の指定方法 auto / fix / specified
    var_axis_value = tk.IntVar()                # 縦軸の高さ
    var_mean_time = tk.StringVar()             # 集計時間単位（n分平均）
    var_from = tk.StringVar()             # 集計開始日
    var_to = tk.StringVar()             # 集計終了日

    # tkinterのウィジェット設定

    # 機器情報
    target_frame = InformationFrame(master=root, text='機器情報')
    target_frame.grid(row=0, column=0)

    # ファイル情報
    fileinfo_frame = InformationFrame(master=root, text='CSV情報')
    fileinfo_frame.write(['', '', '', '', '', ''])  # 5行分の空情報を表示
    fileinfo_frame.grid(row=0, column=1)

    # 集計単位の選択
    SelectMeanTimeFrame(master=root).grid(row=1, column=0)

    # 期間指定
    period_frame = SelectOutputPeriodFrame(master=root)
    period_frame.grid(row=1, column=1)

    # 縦軸スケールの選択
    SelectAxisScaleFrame(master=root).grid(row=2, column=0, columnspan=2)

    # メッセージ表示窓
    msg_frame = MyScrolledText(master=root, width=80, height=10)
    msg_frame.grid(row=3, column=0, columnspan=2)

    # 実行ボタン
    button_frame = ButtonFrame(
        target_frame,
        fileinfo_frame,
        period_frame,
        msg_frame,
        master=root,
    )
    button_frame.grid(row=4, column=0, columnspan=2, ipady=2, padx=2, pady=2)

    root.title('STG集計ツール')
    root.resizable(width=False, height=False)
    root.deiconify()
    root.mainloop()
