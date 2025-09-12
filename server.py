from flask import Flask, render_template, url_for, session, redirect, flash, request, jsonify
import os, random
from uuid import uuid4
import pandas as pd

app = Flask(__name__)
app.secret_key = "your_secret_key"   # 必须要有 session 才能用

# === 游戏全局状态 ===
game_state = {
    "user_images": {},        # user_id -> 已选择的图片
    "assigned_images": set(), # 已分配出去的图片
    "player_count": 1,        # 玩家总数
    "current_players": set()  # 本局已进入的玩家
}

# === 数据加载 ===
DATA_PATH = "C:/Users/33912/PycharmProjects/SGS/data/data_core.xlsx"
heroes_df = pd.read_excel(DATA_PATH)

def get_available_images(difficulty_list, exclude_assigned=True):
    """根据难度获取可用图片路径"""
    df = heroes_df[heroes_df["is_open"] == 1].copy()

    # 按难度筛选
    df_filtered = df[df["difficulty"].isin(difficulty_list)]
    if df_filtered.empty:
        df_filtered = df

    # 生成路径
    df_filtered["path"] = df_filtered.apply(
        lambda row: f"images/{row['id']:03d}_{row['file_name']}.png", axis=1
    )

    # 排除已分配
    if exclude_assigned:
        df_filtered = df_filtered[~df_filtered["path"].isin(game_state["assigned_images"])]

    return df_filtered["path"].tolist()


def init_new_game_if_needed():
    """判断是否需要开启新一局"""
    if len(game_state["current_players"]) >= game_state["player_count"] and game_state["player_count"] > 0:
        game_state["assigned_images"].clear()
        game_state["user_images"].clear()
        game_state["current_players"].clear()


@app.route('/')
def start():
    return render_template("starter.html")


@app.route('/start_game')
def start_game():
    user_id = str(uuid4())
    session['user_id'] = user_id

    # 获取参数
    hero_count = request.args.get("heroCount", default=5, type=int)
    change_count = request.args.get("changeCount", default=0, type=int)
    difficulty = request.args.get("difficulty", default="1,2,3,4,5")

    session['settings'] = {
        "heroCount": hero_count,
        "changeCount": change_count,
        "difficulty": [int(x) for x in difficulty.split(",") if x.isdigit()]
    }

    # 检查是否要开启新一局
    init_new_game_if_needed()

    # 更新玩家状态
    game_state["current_players"].add(user_id)
    game_state["player_count"] = max(game_state["player_count"], len(game_state["current_players"]))

    # 跳转到选择界面
    return redirect(url_for('select'))


@app.route('/select')
def select():
    user_id = session.get("user_id")
    settings = session.get("settings", {})
    if not user_id or not settings:
        return redirect(url_for("start"))

    # ⚡ 如果用户已经确认过选择，禁止回到选择界面，直接进入 /images
    if user_id in game_state["user_images"]:
        return redirect(url_for("character"))

    hero_count = settings.get("heroCount", 5)
    change_count = settings.get("changeCount", 0)
    difficulty_list = settings.get("difficulty", [1, 2, 3, 4, 5])

    # 如果用户之前已经抽过候选，就直接返回之前的
    selected_images = session.get("candidate_images")
    if not selected_images:
        candidates = get_available_images(difficulty_list)
        if not candidates:
            return "❌ 没有符合条件的武将可选"

        # 随机选 hero_count + change_count 个
        total_count = hero_count + change_count
        selected_images = random.sample(candidates, min(total_count, len(candidates)))
        session['candidate_images'] = selected_images  # 记录候选

    return render_template(
        "select.html",
        heroCount=hero_count,
        candidates=selected_images,
        totalCount=len(selected_images)
    )


@app.route('/confirm_selection', methods=["POST"])
def confirm_selection():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("start"))

    data = request.get_json()
    selected = data.get("selected")
    if not selected:
        return jsonify({"error": "未选择武将"}), 400

    # 确保不重复
    if selected in game_state["assigned_images"]:
        return jsonify({"error": "该武将已被选择"}), 400

    game_state["user_images"][user_id] = selected
    game_state["assigned_images"].add(selected)

    # 不清除候选，等进入 /images 再清
    return jsonify({"success": True})


@app.route('/resume_game')
def resume_game():
    user_id = session.get("user_id")
    if user_id and user_id in game_state["user_images"]:
        return redirect(url_for('character'))
    else:
        flash("⚠️ 没有找到已保存的游戏，请先点击开始游戏")
        return redirect(url_for('start'))


@app.route('/images')
def character():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("start"))

    chosen = game_state["user_images"].get(user_id)
    if not chosen:
        return "❌ 你还没有选择武将"

    # ⚡ 用户已经完成选择，清除候选缓存
    session.pop("candidate_images", None)

    return render_template("main.html", image_file=chosen)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
