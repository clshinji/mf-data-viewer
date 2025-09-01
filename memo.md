# Google Drive からコピーしてくる

```bash
rm -rf csv
cp -r "/Users/kentaro/Library/CloudStorage/GoogleDrive-clshinji@gmail.com/マイドライブ/_共有NGYM/03おかね/Moneyfoward/csv" ./csv
```

```bash
cp ./mf_all_data.csv "/Users/kentaro/Library/CloudStorage/GoogleDrive-clshinji@gmail.com/マイドライブ/_共有NGYM/03おかね/Moneyfoward/mf_all_data.csv"
```


csv/ 内のcsvを結合したmf_all_data.csvがあります。このmf_all_data.csvを分析できるstreamlitアプリを作りました。mf_all_data.csvを他の人に有してstreamlitアプリと同じようにデータ分析できるアプリを作っています。まずは、コードベースから現状を確認してください。
