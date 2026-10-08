"""P0 练习：同时使用多个样本训练，并检查未参与训练的输入。

在项目根目录运行：
    learning/.venv/bin/python learning/exercises/03_batch_training.py

目标：让 w 接近 4，并检查 x=5 时是否预测接近 20。
循环中 TODO 尚未补全时，只会显示初始参数对应的结果。
"""

import torch


def main() -> None:
    # 四个样本放在一个一维 Tensor 中，每一对对应一个输入与目标。
    x = torch.tensor([1.0, 2.0, 3.0, 4.0], dtype=torch.float64)
    target = torch.tensor([4.0, 8.0, 12.0, 16.0], dtype=torch.float64)

    w = torch.tensor(2.0, dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.SGD([w], lr=0.01)
    num_steps = 50

    print("训练输入：", x.tolist())
    print("训练目标：", target.tolist())
    print("请补全循环中的 TODO，再观察参数与损失的变化。")

    for step in range(1, num_steps + 1):
        optimizer.zero_grad()

        # TODO 1：用 x 和 w 计算 prediction，它应包含四个预测值。

        # TODO 2：计算每个样本的平方误差，再用 .mean() 得到平均损失 loss。
        # mean() 把四个误差的平方取平均，得到一个标量，供 backward() 使用。

        # TODO 3：计算梯度，再更新参数，参考 02_autograd.py。

        # TODO 4：每隔 10 步打印更新后的 w 和重新计算的平均损失。
        # if step % 10 == 0:
        #     ...
        pass

    # 未参与训练的输入，只用于检查，不进行梯度计算或参数更新。
    with torch.no_grad():
        unseen_x = torch.tensor(5.0, dtype=torch.float64)
        unseen_prediction = unseen_x * w
    print(f"当前 w={w.item():.6f}")
    print(f"未参与训练的输入 x=5，预测={unseen_prediction.item():.6f}，目标=20")


if __name__ == "__main__":
    main()
