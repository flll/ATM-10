#!/usr/bin/env python3
"""
SNBTファイルのgit diff比較ツール
特定のコミット間で言語ファイルの差分を確認する
"""

import subprocess
import sys
import os
import argparse
from typing import Optional, List


def run_git_diff(old_commit: str, new_commit: str, file_path: str) -> str:
    """
    git diffコマンドを実行して差分を取得
    
    Args:
        old_commit: 古いコミットのハッシュ
        new_commit: 新しいコミットのハッシュ
        file_path: 差分を確認したいファイルのパス
    
    Returns:
        差分の文字列
    """
    try:
        cmd = ["git", "diff", old_commit, new_commit, "--", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"エラー: git diffの実行に失敗しました: {e}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)


def parse_diff_output(diff_output: str) -> dict:
    """
    git diffの出力を解析して、追加・削除された行を抽出
    
    Args:
        diff_output: git diffの出力
    
    Returns:
        {'added': [追加された行], 'removed': [削除された行]}
    """
    added_lines = []
    removed_lines = []
    
    for line in diff_output.split('\n'):
        if line.startswith('+') and not line.startswith('+++'):
            # 追加された行
            added_lines.append(line[1:])
        elif line.startswith('-') and not line.startswith('---'):
            # 削除された行
            removed_lines.append(line[1:])
    
    return {
        'added': added_lines,
        'removed': removed_lines
    }


def extract_quest_changes(diff_data: dict) -> dict:
    """
    差分からクエスト関連の変更を抽出
    
    Args:
        diff_data: parse_diff_outputの結果
    
    Returns:
        クエストIDをキーとした変更内容の辞書
    """
    quest_changes = {}
    
    # 追加されたクエストを検出
    for line in diff_data['added']:
        stripped_line = line.strip()
        if stripped_line and not stripped_line.startswith('//'):  # コメント行を除外
            # クエストIDのパターンを検出（例: quest.XXXXX.title: "テキスト"）
            if stripped_line.startswith('quest.') and ':' in stripped_line:
                parts = stripped_line.split(':', 1)
                if len(parts) == 2:
                    # quest.XXXXX.title -> XXXXX
                    quest_parts = parts[0].split('.')
                    if len(quest_parts) >= 2:
                        quest_id = quest_parts[1]
                        quest_type = quest_parts[2] if len(quest_parts) > 2 else 'unknown'
                        content = f"{quest_type}: {parts[1].strip()}"
                        if quest_id not in quest_changes:
                            quest_changes[quest_id] = {'added': [], 'removed': []}
                        quest_changes[quest_id]['added'].append(content)
    
    # 削除されたクエストを検出
    for line in diff_data['removed']:
        stripped_line = line.strip()
        if stripped_line and not stripped_line.startswith('//'):
            if stripped_line.startswith('quest.') and ':' in stripped_line:
                parts = stripped_line.split(':', 1)
                if len(parts) == 2:
                    quest_parts = parts[0].split('.')
                    if len(quest_parts) >= 2:
                        quest_id = quest_parts[1]
                        quest_type = quest_parts[2] if len(quest_parts) > 2 else 'unknown'
                        content = f"{quest_type}: {parts[1].strip()}"
                        if quest_id not in quest_changes:
                            quest_changes[quest_id] = {'added': [], 'removed': []}
                        quest_changes[quest_id]['removed'].append(content)
    
    return quest_changes


def display_changes(quest_changes: dict, show_all: bool = False):
    """
    変更内容を見やすく表示
    
    Args:
        quest_changes: クエストの変更内容
        show_all: すべての変更を表示するか（Falseの場合は要約のみ）
    """
    if not quest_changes:
        print("変更はありません。")
        return
    
    print(f"\n=== クエストの変更概要 ===")
    print(f"変更されたクエスト数: {len(quest_changes)}")
    
    added_quests = [qid for qid, changes in quest_changes.items() 
                   if changes['added'] and not changes['removed']]
    removed_quests = [qid for qid, changes in quest_changes.items() 
                     if changes['removed'] and not changes['added']]
    modified_quests = [qid for qid, changes in quest_changes.items() 
                      if changes['added'] and changes['removed']]
    
    if added_quests:
        print(f"\n新規追加: {len(added_quests)}件")
        if show_all:
            for qid in added_quests[:10]:  # 最初の10件を表示
                print(f"  - {qid}")
            if len(added_quests) > 10:
                print(f"  ... 他 {len(added_quests) - 10}件")
    
    if removed_quests:
        print(f"\n削除: {len(removed_quests)}件")
        if show_all:
            for qid in removed_quests[:10]:
                print(f"  - {qid}")
            if len(removed_quests) > 10:
                print(f"  ... 他 {len(removed_quests) - 10}件")
    
    if modified_quests:
        print(f"\n変更: {len(modified_quests)}件")
        if show_all:
            for qid in modified_quests[:10]:
                print(f"  - {qid}")
            if len(modified_quests) > 10:
                print(f"  ... 他 {len(modified_quests) - 10}件")


def main():
    parser = argparse.ArgumentParser(
        description='SNBTファイルのgit diff比較ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用例:
  # 2つのコミット間でen_us.snbtの差分を確認
  python snbt_git_lang_compare.py cfca31a3b5ae0 32078db080711 en_us.snbt
  
  # ja_jp.snbtの差分を詳細表示
  python snbt_git_lang_compare.py cfca31a3b5ae0 32078db080711 ja_jp.snbt --verbose
  
  # 生のdiff出力を表示
  python snbt_git_lang_compare.py cfca31a3b5ae0 32078db080711 en_us.snbt --raw
        '''
    )
    
    parser.add_argument('old_commit', help='比較元のコミットハッシュ')
    parser.add_argument('new_commit', help='比較先のコミットハッシュ')
    parser.add_argument('file', help='比較するファイル名（例: en_us.snbt）')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='詳細な変更内容を表示')
    parser.add_argument('-r', '--raw', action='store_true',
                       help='git diffの生の出力を表示')
    parser.add_argument('-p', '--path', default='config/ftbquests/quests/lang',
                       help='ファイルのパス（デフォルト: config/ftbquests/quests/lang）')
    
    args = parser.parse_args()
    
    # ファイルパスを構築
    if not args.file.endswith('.snbt'):
        args.file += '.snbt'
    
    file_path = os.path.join(args.path, args.file)
    
    print(f"比較中: {args.old_commit} → {args.new_commit}")
    print(f"ファイル: {file_path}")
    
    # git diffを実行
    diff_output = run_git_diff(args.old_commit, args.new_commit, file_path)
    
    if not diff_output:
        print("\n差分はありません。")
        return
    
    if args.raw:
        # 生のdiff出力を表示
        print("\n=== Git Diff Output ===")
        print(diff_output)
    else:
        # 差分を解析して表示
        diff_data = parse_diff_output(diff_output)
        quest_changes = extract_quest_changes(diff_data)
        display_changes(quest_changes, show_all=args.verbose)
        
        # 統計情報
        print(f"\n=== 統計情報 ===")
        print(f"追加された行数: {len(diff_data['added'])}")
        print(f"削除された行数: {len(diff_data['removed'])}")


if __name__ == "__main__":
    main()