# 团队开发流程规范

## 1. 主分支说明
- 仓库的 **主分支为 `master`**。  
- `master` 分支只存放经过审核、稳定的代码。  
- **禁止直接在 `master` 分支进行开发或提交代码**。  

---

## 2. 分支命名规范
- 每个成员在开发新功能或修复 Bug 时，都需要创建一个独立分支进行开发。  
- 分支命名规则：  
debug-xxx
其中 `xxx` 为开发人员名字的 **拼音首字母**。  
- 例如：张三 → `debug-zs`  
- 李四 → `debug-ls`  

---

## 3. 开发流程

### Step 1：拉取项目代码
第一次参与项目时，先克隆仓库：
```bash
git clone https://github.com/SMStudent117/SGS-Card-Distributer.git
cd 仓库名
如果仓库已经存在，更新最新代码：
git checkout master
git pull origin master
```
### Step 2：创建开发分支

从 master 分支拉取最新代码后，新建属于自己的开发分支：
```bash
git checkout master
git pull origin master
git checkout -b debug-xxx
```
### Step 3：在开发分支上进行开发

所有功能开发、Bug 修复都在自己的 debug-xxx 分支上完成。

修改完成后提交代码：
```bash
git add .
git commit -m "本次修改的简要说明"
```
推送到远程仓库：
```bash
git push origin debug-xxx
```
### Step 4：提交 Pull Request（PR）

登录 GitHub → 打开仓库 → 切换到自己的 debug-xxx 分支。

点击 Compare & pull request。

确认 base 分支是 master，compare 分支是 debug-xxx。

填写本次修改说明，点击 Create pull request。

等待代码审核。审核通过后，由仓库管理员合并到 master 分支。

⚠️ 注意：不要直接 push 到 master，必须通过 Pull Request 审查后合并。

## 4. 更新分支代码

当 master 有其他人合并的新代码时，需要更新自己的分支：
```bash
# 切换到 master 分支并拉取最新代码
git checkout master
git pull origin master

# 切换回自己的开发分支并合并最新的 master
git checkout debug-xxx
git merge master
```
如果有冲突，请手动解决冲突后再提交：
```bash
git add .
git commit -m "解决冲突"
git push origin debug-xxx
```

## 5. 注意事项

开发前务必先更新 master，避免分支落后太多。

分支命名要统一，遵循 debug-xxx 格式。

每次提交的 commit message 要简洁明了，说明本次修改内容。

所有代码必须通过 Pull Request 审查后才能进入 master。
