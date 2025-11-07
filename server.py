from flask import Flask, render_template, url_for, session, redirect, flash, request, jsonify
import os, random
from uuid import uuid4
import pandas as pd

app = Flask(__name__)
app.secret_key = "your_secret_key"   # 必须要有 session 才能用

game_state = {
    "user_images": {},        # user_id -> 已选择的图片
    "assigned_images": set(), # 已最终分配出去的图片
    "shown_images": set(),    # 已经展示过的候选图片
    "player_count": 1,
    "current_players": set(),
    "user_roles": {},
    "user_status": {},        # user_id -> 状态 ("lobby", "choosing", "in_game")
    "round_finished": False   # 本局是否结束
}

GLOBAL_HERO_COUNT = 5          # 选将框数量
GLOBAL_CHANGE_COUNT = 5        # 换将卡数量
# === 数据加载 ===
# DATA_PATH = "C:/Users/33912/PycharmProjects/SGS/data/data_debug.xlsx"
DATA_PATH = "C:/Users/33912/PycharmProjects/SGS/data/data_core.xlsx"
heroes_df = pd.read_excel(DATA_PATH)

# ==== 新增: 根据人数生成身份池 ====
def generate_roles(player_count):
    if player_count == 5:
        return ["主公", "忠臣", "反贼", "反贼", "内奸"]
    if player_count == 4:
        return ["主公","忠臣","反贼","反贼"]
    if player_count == 3:
        return ["主公", "内奸", "反贼"]
    if player_count == 2:
        return ["主公", "反贼"]
    if player_count == 1:
        return ["主公"]
    # 其他人数规则可以自行扩展
    return ["主公", "忠臣", "反贼", "  内奸"][:player_count]

def get_available_images(difficulty_list, exclude_shown=True):
    df = heroes_df[heroes_df["is_open"] == 1].copy()

    # 按难度筛选
    df_filtered = df[df["difficulty"].isin(difficulty_list)]
    if df_filtered.empty:
        df_filtered = df

    # 生成路径
    df_filtered["path"] = df_filtered.apply(
        lambda row: f"images/{row['id']:03d}_{row['file_name']}.png", axis=1
    )

    # 排除已展示过的
    if exclude_shown:
        df_filtered = df_filtered[~df_filtered["path"].isin(game_state["shown_images"])]

    return df_filtered["path"].tolist()


def init_new_game_if_needed():
    """判断是否需要开启新一局"""
    if game_state.get("round_finished"):
        # ⚡ 开启新一局
        game_state["assigned_images"].clear()
        game_state["shown_images"].clear()
        game_state["user_images"].clear()
        game_state["current_players"].clear()
        game_state["user_roles"].clear()
        game_state["user_status"].clear()  # 清空用户状态
        game_state["round_finished"] = False
        print("⚡ 新的一局开始，所有身份和角色记录已清空")

def print_available_images():
    """调试输出剩余可选图片情况"""
    df = heroes_df[heroes_df["is_open"] == 1].copy()

    # 每个难度的总数
    total_by_diff = df.groupby("difficulty")["id"].count().to_dict()

    # 已展示的
    shown = game_state["shown_images"]

    # 每个难度已展示
    df["path"] = df.apply(lambda row: f"images/{row['id']:03d}_{row['file_name']}.png", axis=1)
    used = df[df["path"].isin(shown)].groupby("difficulty")["id"].count().to_dict()

    # 按照难度排序输出
    result_parts = []
    for diff in sorted(total_by_diff.keys()):
        used_count = used.get(diff, 0)
        total_count = total_by_diff[diff]
        result_parts.append(f"{used_count}/{total_count}")

    print("available (shown/total):", " | ".join(result_parts))


@app.route('/')
def start():
    user_id = session.get("user_id")
    # 新用户首次访问，分配uuid并设置状态为lobby
    if not user_id:
        user_id = str(uuid4())
        session['user_id'] = user_id
        game_state["user_status"][user_id] = "lobby"
        game_state["current_players"].add(user_id)
    return render_template("base_starter.html")


@app.route('/start_game')
def start_game():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for('start'))

    # 获取参数
    difficulty = request.args.get("difficulty", default="1,2,3,4,5")

    session['settings'] = {
        "heroCount": GLOBAL_HERO_COUNT,
        "changeCount": GLOBAL_CHANGE_COUNT,
        "difficulty": [int(x) for x in difficulty.split(",") if x.isdigit()]
    }

    # 检查是否要开启新一局
    init_new_game_if_needed()

    # 更新玩家状态
    game_state["current_players"].add(user_id)
    game_state["player_count"] = max(game_state["player_count"], len(game_state["current_players"]))

    # === 身份分配在这里完成 ===
    if user_id not in game_state["user_roles"]:
        total_players = game_state["player_count"]
        assigned_roles = list(game_state["user_roles"].values())
        role_pool = generate_roles(total_players)
        remaining_roles = [r for r in role_pool if assigned_roles.count(r) < role_pool.count(r)]
        if remaining_roles:
            game_state["user_roles"][user_id] = random.choice(remaining_roles)

    # 设置状态为choosing并跳转到选择界面
    game_state["user_status"][user_id] = "choosing"
    return redirect(url_for('select'))


@app.route('/select')
def select():
    user_id = session.get("user_id")
    settings = session.get("settings", {})
    if not user_id or not settings:
        return redirect(url_for("start"))

    # 检查用户状态，非choosing状态不允许访问
    if game_state["user_status"].get(user_id) != "choosing":
        return redirect(url_for("start"))

    # 如果用户已经确认过选择，禁止停留在选择界面
    if user_id in game_state["user_images"]:
        return redirect(url_for("character"))

    hero_count = settings.get("heroCount", 5)
    change_count = settings.get("changeCount", 0)
    difficulty_list = settings.get("difficulty", [1, 2, 3, 4, 5])

    selected_images = session.get("candidate_images")
    if not selected_images:
        candidates = get_available_images(difficulty_list)
        if not candidates:
            return "❌ 没有符合条件的武将可选"

        total_count = hero_count + change_count
        selected_images = random.sample(candidates, min(total_count, len(candidates)))
        session['candidate_images'] = selected_images

        # 🚀 记录为已展示过的
        game_state["shown_images"].update(selected_images)
        print_available_images()
    # 把身份传给前端
    role = game_state["user_roles"].get(user_id)
    if role != "主公":
        return render_template(
            "base_selecter.html",
            heroCount=hero_count,
            candidates=selected_images,
            totalCount=len(selected_images),
            role=role
        )
    else:
        return render_template(
            "zhugong_selecter.html",
            heroCount=hero_count,
            candidates=selected_images,
            totalCount=len(selected_images),
            role=role
        )

@app.route('/confirm_selection', methods=["POST"])
def confirm_selection():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("start"))

    # 检查用户状态
    if game_state["user_status"].get(user_id) != "choosing":
        return jsonify({"error": "无效的操作状态"}), 400

    data = request.get_json()
    selected = data.get("selected")
    print(selected)
    if not selected:
        return jsonify({"error": "未选择武将"}), 400

    # 确保唯一性
    if selected in game_state["assigned_images"]:
        return jsonify({"error": "该武将已被选择"}), 400

    # 保存选择
    game_state["user_images"][user_id] = selected
    game_state["assigned_images"].add(selected)

    # 分配身份（保持原有逻辑）
    if user_id not in game_state["user_roles"]:
        total_players = game_state["player_count"]
        assigned_roles = list(game_state["user_roles"].values())
        role_pool = generate_roles(total_players)
        remaining_roles = [r for r in role_pool if assigned_roles.count(r) < role_pool.count(r)]
        if remaining_roles:
            role = random.choice(remaining_roles)
            game_state["user_roles"][user_id] = role

    # 更新状态为in_game
    game_state["user_status"][user_id] = "in_game"

    if len(game_state["user_images"]) >= game_state["player_count"]:
        game_state["round_finished"] = True
        print("✅ 所有人已选完，等待下一局开始")

    return jsonify({"success": True})


@app.route('/resume_game')
def resume_game():
    user_id = session.get("user_id")
    if not user_id:
        flash("⚠️ 没有找到已保存的游戏，请先点击开始游戏")
        return redirect(url_for('start'))

    # 根据用户状态处理不同的恢复逻辑
    status = game_state["user_status"].get(user_id)
    if status == "lobby":
        flash("⚠️ 没有找到已保存的游戏，请先点击开始游戏")
        return redirect(url_for('start'))
    elif status == "choosing":
        return redirect(url_for('select'))
    elif status == "in_game":
        return redirect(url_for('character'))
    else:
        flash("⚠️ 状态异常，请重新开始游戏")
        return redirect(url_for('start'))


@app.route('/images')
def character():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("start"))

    # 检查用户状态
    if game_state["user_status"].get(user_id) != "in_game":
        return redirect(url_for("start"))

    chosen = game_state["user_images"].get(user_id)
    role = game_state["user_roles"].get(user_id)
    if not chosen:
        return "❌ 你还没有选择武将"

    session.pop("candidate_images", None)

    # === 新逻辑：检查 ui_style ===
    try:
        # 从 chosen 路径解析出 id
        # 路径形如 images/001_xxx.png → 提取 id=1
        file_name = os.path.basename(chosen)  # 001_xxx.png
        hero_id = int(file_name.split("_")[0])  # 前3位数字
        row = heroes_df.loc[heroes_df["id"] == hero_id].iloc[0]

        if row["ui_style"] == 1:
            # 生成 a 和 b 的路径
            image_file_a = chosen
            next_id = hero_id + 1
            row2 = heroes_df.loc[heroes_df["id"] == next_id].iloc[0]
            image_file_b = f"images/{row2['id']:03d}_{row2['file_name']}.png"

            return render_template(
                "main_ab.html",
                image_file_a=image_file_a,
                image_file_b=image_file_b,
                role=role
            )
        if row["ui_style"] == 2:
            # 1. 计算起始行（当前行id减5，至少为1）
            start_id = max(hero_id - 5, 1)
            # 获取从起始id开始的所有行（按id升序遍历）
            # 假设id是连续的，这里通过id筛选实现从start_id开始遍历
            filtered_df = heroes_df[heroes_df["id"] >= start_id].sort_values("id")

            chosen_skills = []
            # 2. 遍历查找符合条件的行
            for idx, current_row in filtered_df.iterrows():
                if current_row["parent_id"] == hero_id and current_row["id"] != current_row["parent_id"]:
                    # 符合条件，合成图片路径
                    skill_path = f"static/images/{current_row['id']:03d}_{current_row['file_name']}.png"
                    chosen_skills.append(skill_path)
                else:
                    # 不符合条件，结束查找
                    break

            # 3. 渲染页面并传递skills参数
            return render_template(
                "base_game_skill.html",
                image_file=chosen,
                role=role,
                skills=chosen_skills
            )
    except Exception as e:
        print("ui_style 检查失败:", e)

    # 默认逻辑（ui_style==0 或异常时）
    return render_template("base_game_v3.html", image_file=chosen, role=role)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)