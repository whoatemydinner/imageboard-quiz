import re


def logging_message(obj, message):
    print("{}: {}".format(obj.__class__.__name__, message))


def format_comment(text: str):
    comment = re.sub(r"<a.*?>", "", text)
    comment = re.sub(r"<br>", "\n", comment)
    comment = re.sub(r"<wbr>", "", comment)
    comment = re.sub(r"<span.*?>", "", comment)
    comment = re.sub(r"</.*?>", "", comment)
    comment = comment.replace("&gt;", ">")
    comment = comment.replace("&#039;", "'")
    comment = comment.replace("&quot;", "\"")
    return comment


if __name__ == "__main__":
    pass
