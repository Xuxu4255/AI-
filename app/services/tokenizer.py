import jieba


def split_question(question: str):
    return jieba.lcut(question)



#测试
if __name__ == "__main__":
    print(split_question("栈和队列有啥区别"))