from JdSession import Session

if __name__ == '__main__':

    skuId = '10032192754328'
    skuNum = 1
    areaId = '1_2901_4135'

    sess = Session()
    sess.item_details[skuId] = sess._get_item_detail(skuId)

    sess.prepareCart(skuId, skuNum, areaId)