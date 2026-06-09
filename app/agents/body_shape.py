def classify_body_shape(bust, waist, hip):

    if hip > bust + 5:
        return "Pear"

    elif bust > hip + 5:
        return "Inverted Triangle"

    elif abs(bust - hip) <= 2:
        return "Hourglass"

    else:
        return "Rectangle"
