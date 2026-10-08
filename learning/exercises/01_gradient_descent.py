"""P0 练习：用纯 Python 完成 10 次梯度下降更新。

运行方式（在项目根目录执行）：
    python3 learning/exercises/01_gradient_descent.py

补全循环中的 TODO。目标是观察 w 逐渐接近 4、损失逐渐接近 0。
"""


def main() -> None:
    x = 3
    target_value = 12
    w = 2.0
    learning_rate = 0.01
    num_steps = 10

    initial_prediction = x * w
    initial_loss = (initial_prediction - target_value) ** 2
    print(f"初始：w={w:.4f}，预测={initial_prediction:.4f}，损失={initial_loss:.4f}")

    for step in range(1, num_steps + 1):
        # TODO 1：使用当前 w 计算 prediction。
        prediction = x * w

        # TODO 2：计算当前 loss。Python 中平方用 ** 2。
        loss = (prediction - target_value) ** 2

        # TODO 3：计算 gradient = 2 * (prediction - target_value) * x。
        gradient = 2 * (prediction - target_value) * x

        # TODO 4：更新 w，使下一轮使用这次更新后的参数。
        w = w - learning_rate * gradient

        # TODO 5：用新的 w 重新计算 prediction 和 loss。
        prediction = x * w
        loss = (prediction - target_value) ** 2

        # TODO 6：打印 step、更新后的 w、prediction 和 loss。
        # 可以参考上面的 print 写法。
        print(f'更新后 {step} 的 w:', w)
        print(f'更新后 {step} 的 prediction:', prediction)
        print(f'更新后{step} 的 loss:', loss)


if __name__ == "__main__":
    main()
