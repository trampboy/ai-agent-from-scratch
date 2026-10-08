"""P0 练习：用 PyTorch 自动求导重做一次参数更新。

在项目根目录运行：
    learning/.venv/bin/python learning/exercises/02_autograd.py

先补全三个 TODO，保持 num_steps=1，观察 backward 前后及 step 后的变化。
单步结果正确后再将 num_steps 改成 10，与 01_gradient_descent.py 对照。
"""

import torch


def main() -> None:
    x = 3.0
    target_value = 12.0
    learning_rate = 0.01
    num_steps = 10

    # Tensor 是 PyTorch 的数值容器；本例只存一个数。
    # requires_grad=True 表示需要计算损失对 w 的梯度。
    # 使用 float64，便于与上一份 Python 浮点练习对照。
    w = torch.tensor(2.0, dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.SGD([w], lr=learning_rate)

    for step in range(1, num_steps + 1):
        # TODO 1：调用 optimizer.zero_grad()，清除上一轮留下的梯度。
        optimizer.zero_grad()

        prediction = x * w
        loss = (prediction - target_value) ** 2
        print(f"第 {step} 步，backward 前：w={w.item():.6f}，损失={loss.item():.6f}")

        # TODO 2：调用 loss.backward()，自动计算梯度。
        # 不再手写 gradient = 2 * (prediction - target_value) * x。
        loss.backward()

        gradient = None if w.grad is None else w.grad.item()
        print(f"backward 后：w={w.item():.6f}，w.grad={gradient}")

        # TODO 3：调用 optimizer.step()，根据梯度更新参数。
        # 不再手写 w = w - learning_rate * gradient。
        optimizer.step()

        # 这里只查看更新后的结果，无需记录供反向传播使用的计算过程。
        with torch.no_grad():
            new_prediction = x * w
            new_loss = (new_prediction - target_value) ** 2
        print(
            f"step 后：w={w.item():.6f}，"
            f"预测={new_prediction.item():.6f}，损失={new_loss.item():.6f}"
        )


if __name__ == "__main__":
    main()
