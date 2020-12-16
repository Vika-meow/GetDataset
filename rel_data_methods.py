import random
from conf import *
from data_utils import *


def remove_dbo_triples(rel_triples):
    ib_triples = set()
    for triple in rel_triples:
        if DBO_PREFIX not in triple[1]:
            ib_triples.add(triple)
    return ib_triples


def generate_all_rel_triples(folder, lines, ent_t_prefix):
    """
    Filter to get all rel triples and write to file
    :param folder:
    :param lines:
    :param ent_t_prefix: Target object uri prefix
    :return:
    """
    assert os.path.exists(folder)
    rel_triples, rel_lines = parse_rel_ttl_2set_from_lines(lines, ent_t_prefix)
    print("all rel triples:", len(rel_triples))
    print("write all rel triples to file...")
    triples_2file(rel_triples, folder + ALL_REL_TRIPLES_FILE)
    del rel_triples
    print("Done!")
    return rel_lines


def parse_rel_ttl_2set_from_lines(lines, ent_t_prefix):
    rel_triples = set()
    rel_lines = set()
    for line in lines:
        triple = parse_ttl_lines(line)
        if triple[2].startswith(ent_t_prefix) and 'dbpedia.org' in triple[1]:
            rel_triples.add(triple)
            rel_lines.add(line)
    return rel_triples, rel_lines


def generate_all_rel_data_set(kb12_folder, kb1_folder, kb2_folder, ills_num=15000):
    path = radio_2file(ills_num, kb12_folder)

    source_triples = read_triples(path + S_TRIPLES)
    target_triples = read_triples(path + T_TRIPLES)
    matched_ents = read_pairs(path + ENT_ILLS)
    ents1, ents2 = pair_2set(matched_ents)
    assert len(matched_ents) == len(ents1) == len(ents2) == ills_num

    print_line("begin all data set...")
    all_x_rel_triples = kb1_folder + ALL_REL_TRIPLES_FILE
    all_en_rel_triples = kb2_folder + ALL_REL_TRIPLES_FILE
    # remove dbo triples
    all_source_triples = remove_dbo_triples(read_triples(all_x_rel_triples)) | source_triples
    all_target_triples = remove_dbo_triples(read_triples(all_en_rel_triples)) | target_triples
    print("all source ib rel triples", len(all_source_triples))
    print("all target ib rel triples", len(all_target_triples))
    all_source_triples = filter_triples_by_heads(all_source_triples, ents1)
    all_target_triples = filter_triples_by_heads(all_target_triples, ents2)
    heads1, _, _ = parse_triples_heads(all_source_triples)
    heads2, _, _ = parse_triples_heads(all_target_triples)
    print("heads1", len(heads1), "heads2", len(heads2))
    assert len(heads1) == len(heads2) == ills_num
    assert len(ents1 - heads1) == len(ents2 - heads2) == 0

    data_set_folder = path + DATA_SET_FOLDER
    if not os.path.exists(data_set_folder):
        os.makedirs(data_set_folder)
    print("all source rel triples", len(all_source_triples))
    print("all target rel triples", len(all_target_triples))
    triples_2file(all_source_triples, data_set_folder + S_TRIPLES)
    triples_2file(all_target_triples, data_set_folder + T_TRIPLES)
    pairs_2file(matched_ents, data_set_folder + ENT_ILLS)


def generate_source_en_train_triples(data_folder, x_rel_triples, ill_file, en_rel_triples, filter_th1, filter_th2,
                                     min_sub=1,
                                     is_matched_close=False, ills_num=15000, target_ills_num=15000,
                                     ills_t_prefix='http://dbpedia.org/resource/', is_remove=False):
    source_triples = read_triples(x_rel_triples)
    target_triples = read_triples(en_rel_triples)
    ill_pairs, ill_head_set, ill_tail_set = read_interlink(ill_file, ent_t_prefix=ills_t_prefix)
    # The list of all matching pairs in the current data set is generally less than ill pairs, and the entity pairs are sorted according to degrees, etc.
    print("step 1...")
    matched_ents, matched_rels = generate_matched_heads_ordered(source_triples, target_triples, ill_pairs,
                                                                filter_th=filter_th1)

    if min_sub > 1:
        source_triples = filter_triples_by_min(source_triples, min_sub)
        target_triples = filter_triples_by_min(target_triples, min_sub)
    # Matching is closed, that is, the first and last entities are required to be in the matching pair list
    if is_matched_close is True:
        source_triples = generate_matched_closed_triples(source_triples, matched_ents, 0)
        target_triples = generate_matched_closed_triples(target_triples, matched_ents, 1)
    if min_sub > 1 and is_matched_close is True:
        matched_ents, matched_rels = generate_matched_heads_ordered(source_triples, target_triples, ill_pairs)
    print("ills at step 1", len(matched_ents), "\n")
    assert len(matched_ents) > ills_num

    print("step 2...")
    # Reduce link to ills_num
    # matched_ents = matched_ents[0: ills_num]
    matched_ents = random.sample(matched_ents, ills_num)
    # Extract the triples of the entities in the current links and reduce the KG on both sides
    source_triples, target_triples = filter_triples_by_ill_heads(source_triples, target_triples, matched_ents)
    # Filter out triples of low-degree entities to further reduce the KG on both sides
    if is_remove:
        print("before removing 1 degree", len(source_triples), len(target_triples))
        source_triples = remove_tails_with_1in_degree(source_triples)
        target_triples = remove_tails_with_1in_degree(target_triples)
        print("after removing 1 degree", len(source_triples), len(target_triples))
    # Get the current link left
    current_matched_ents, _ = generate_matched_heads_ordered(source_triples, target_triples, ill_pairs,
                                                             filter_th=filter_th2)
    print("current head ills", len(current_matched_ents))

    assert len(current_matched_ents) > target_ills_num
    matched_ents = current_matched_ents[0:target_ills_num]
    ents1, ents2 = pair_2set(matched_ents)
    source_triples = filter_triples_by_heads(source_triples, ents1)
    target_triples = filter_triples_by_heads(target_triples, ents2)
    matched_ents, matched_rels = generate_matched_heads_ordered(source_triples, target_triples, ill_pairs)
    assert len(matched_ents) == target_ills_num
    ents1, ents2 = pair_2set(matched_ents)
    head1, _, tails1 = parse_triples_heads(source_triples)
    head2, _, tails2 = parse_triples_heads(target_triples)
    assert len(head1 - ents1) == 0 and len(head2 - ents2) == 0

    path = radio_2file(target_ills_num, data_folder)
    triples_2file(source_triples, path + S_TRIPLES)
    triples_2file(target_triples, path + T_TRIPLES)
    pairs_2file(matched_ents, path + ENT_ILLS)
    pairs_2file(matched_rels, path + REL_ILLS)


def generate_matched_rel(kb1_rel, kb2_rels):
    if kb1_rel in kb2_rels:
        return kb1_rel
    else:
        for rel in kb2_rels:
            if is_suffix_equal(rel, kb1_rel):
                return rel
    return None


def generate_closed_triples(folder, rel_triples_set, ill_head_set):
    """
    Filter to get closed triples, that is, triples with head and tail entities in ill
    :param folder:
    :param rel_triples_set:
    :param ill_head_set:
    :return:
    """
    all_closed_triples_set = filter_triples_by_entset(rel_triples_set, ill_head_set)
    print("rel closed triples:", len(all_closed_triples_set))
    print("write rel closed triples to file:", ALL_REL_CLOSED_TRIPLES_FILE)
    triples_2file(all_closed_triples_set, folder + ALL_REL_CLOSED_TRIPLES_FILE)
    print("Done")
    print_line()
    return all_closed_triples_set


def generate_balance_closed_triples(folder, all_closed_triples_set):
    """
    Filter the closed triplets to get the balanced triplets
    :param folder:
    :param all_closed_triples_set:
    :return:
    """
    ib_closed_balanced_triples_set = generate_balanced_triples(all_closed_triples_set)
    print("rel closed balanced triples:", len(ib_closed_balanced_triples_set))
    print("write rel closed balanced triples to file:", ALL_REL_CLOSED_BALANCED_TRIPLES_FILE)
    triples_2file(ib_closed_balanced_triples_set, folder + ALL_REL_CLOSED_BALANCED_TRIPLES_FILE)
    print("Done")
    print_line()


def filter_triples_by_heads(ori_triples, ents_set):
    print("before filtering by heads", len(ori_triples))
    triples = set()
    for triple in ori_triples:
        if triple[0] in ents_set:
            triples.add(triple)
    print("after filtering by heads", len(triples))
    return triples


def remove_triples_by_tails(ori_triples, ents_set):
    triples = set()
    for triple in ori_triples:
        if triple[2] not in ents_set:
            triples.add(triple)
    return triples


def filter_triples_by_ents(ori_triples, ents_set):
    triples = set()
    for triple in ori_triples:
        if triple[0] in ents_set and triple[2] in ents_set:
            triples.add(triple)
    return triples


def filter_triples_by_ill_heads(source_triples, en_triples, matched_ents):
    ents1_set, ents2_set = pair_2set(matched_ents)
    # Filter triplets according to ills, satisfying the head entity are ill entities
    source_triples = filter_triples_by_heads(source_triples, ents1_set)
    en_triples = filter_triples_by_heads(en_triples, ents2_set)
    return source_triples, en_triples


def filter_triples_by_ills(source_triples, en_triples, matched_ents):
    ents1_set, ents2_set = pair_2set(matched_ents)
    # Filter triplets according to ills, satisfying both head and tail entities are ill entities
    source_triples = filter_triples_by_ents(source_triples, ents1_set)
    en_triples = filter_triples_by_ents(en_triples, ents2_set)
    # source_triples = filter_triples_by_heads(source_triples, ents1_set)
    # en_triples = filter_triples_by_heads(en_triples, ents2_set)
    return source_triples, en_triples


def remove_ents(ori_triples, ents_set):
    if len(ents_set) == 0:
        return ori_triples
    triples = set()
    for triple in ori_triples:
        # if not (triple[0] in ents_set or triple[2] in ents_set):
        if not (triple[0] in ents_set):
            triples.add(triple)
    return triples


def filter_triples_by_ills_closed(source_triples, en_triples, matched_ents, current_matched_ents):
    l = len(matched_ents)
    assert len(current_matched_ents) <= l
    remove_matched_ents = list(set(matched_ents) - set(current_matched_ents))
    ents1_set, ent2_set = pair_2set(remove_matched_ents)
    source_triples = remove_ents(source_triples, ents1_set)
    en_triples = remove_ents(en_triples, ent2_set)
    filter_triples_by_ills()
    return source_triples, en_triples


def triples_2dict(triples):
    dic = dict()
    for triple in triples:
        add_dict_kv(dic, triple[0], triple)
    return dic


def get_all_triples(ents, triples_dict):
    all_triples = set()
    for ent in ents:
        assert ent in triples_dict.keys()
        all_triples = all_triples | triples_dict.get(ent)
    heads, rels, tails = parse_triples_heads(all_triples)
    print("heads", len(heads))
    print("rels", len(rels))
    print("tails", len(tails))
    print("ents", len(tails | heads))
    print("triples", len(all_triples))
    return all_triples


def remove_tails_with_1in_degree(triples):
    heads, _, tails = parse_triples_heads(triples)
    dic = generate_related_ents(triples)
    removed_tails = set()
    tails = tails - heads
    for tail in tails:
        assert tail in dic
        related_heads = dic.get(tail)
        if len(related_heads) == 1:
            removed_tails.add(tail)
    print("1 in degree tails", len(removed_tails))
    if len(removed_tails) > 1:
        triples = remove_triples_by_tails(triples, removed_tails)
    # new_heads, _, _ = parse_triples_heads(triples)
    # assert len(heads - new_heads) == 0
    return triples


def generate_balanced_triples(triples):
    """
    Filter to get balanced triplets
    :param triples:
    :return:
    """
    heads, tails = set(), set()
    for triple in triples:
        heads.add(triple[0])
        tails.add(triple[2])
    balanced_ents = heads & tails
    print("heads, tails, balances:", len(heads), len(tails), len(balanced_ents))
    return filter_triples_by_entset(triples, balanced_ents)


def generate_related_ents(triples):
    dic = dict()
    for triple in triples:
        add_dict_kv(dic, triple[0], triple[2])
        add_dict_kv(dic, triple[2], triple[0])
    return dic


def count_degree(ent, ill_ents, related_ents_dict):
    assert ent in related_ents_dict.keys()
    related_ents = related_ents_dict.get(ent)
    return len(related_ents & ill_ents)


def generate_matched_heads_ordered(source_triples, en_triples, ill_pairs, filter_th=1):
    print_line("start to generate current ILLs ...")
    links_dict = pair_2dict(ill_pairs)
    print("total num of ills between kb1 and kb2:", len(links_dict))
    kb1_ents, kb1_rels, tails1 = parse_triples_heads(source_triples)
    kb2_ents, kb2_rels, tails2 = parse_triples_heads(en_triples)
    print("num of triples, heads, ents and rels in kb1:", len(source_triples), len(kb1_ents), len(kb1_ents | tails1),
          len(kb1_rels))
    print("num of triples, heads, ents and rels in kb2:", len(en_triples), len(kb2_ents), len(kb2_ents | tails2),
          len(kb2_rels))
    matched_ents = list()  # 有序的
    matched_rels = list()
    for ent in kb1_ents:
        if ent in links_dict:
            kb2_ent = links_dict.get(ent)
            if kb2_ent in kb2_ents:
                matched_ents.append((ent, kb2_ent))
    print("num of matched ent pairs in kb1 and kb2:", len(matched_ents))

    ents1_set, ents2_set = pair_2set(matched_ents)
    source_related_ents_dict = generate_related_ents(source_triples)
    en_related_ents_dict = generate_related_ents(en_triples)
    ordered_dic = dict()
    for ent1, ent2 in matched_ents:
        degree1 = count_degree(ent1, ents1_set, source_related_ents_dict)
        degree2 = count_degree(ent2, ents2_set, en_related_ents_dict)
        if filter_th > 1:
            if degree1 < filter_th or degree2 < filter_th:
                continue
                # print(degree1, degree2)
        ordered_dic[(ent1, ent2)] = degree1 + degree2
    ordered_pair = sorted(ordered_dic.items(), key=lambda d: d[1], reverse=True)
    ordered_matched_ents = [pair[0] for pair in ordered_pair]

    # Solve the one-to-many problem
    rel_ref_set = set()
    for rel in kb1_rels:
        ref = generate_matched_rel(rel, kb2_rels)
        if ref is not None and ref not in rel_ref_set:
            matched_rels.append((rel, ref))
            rel_ref_set.add(ref)
    print("num of ref rels in kb1 and kb2:", len(matched_rels))
    print_line()
    return ordered_matched_ents, matched_rels


def generate_matched_pairs_ordered(source_triples, en_triples, ill_pairs):
    print_line("start to generate current ILLs ...")
    links_dict = pair_2dict(ill_pairs)
    print("total num of ills between kb1 and kb2:", len(links_dict))
    kb1_ents, kb1_rels = parse_triples(source_triples)
    kb2_ents, kb2_rels = parse_triples(en_triples)
    print("num of triples, ents and rels in kb1:", len(source_triples), len(kb1_ents), len(kb1_rels))
    print("num of triples, ents and rels in kb2:", len(en_triples), len(kb2_ents), len(kb2_rels))
    matched_ents = list()  # Ordered
    matched_rels = list()
    for ent in kb1_ents:
        if ent in links_dict:
            kb2_ent = links_dict.get(ent)
            if kb2_ent in kb2_ents:
                matched_ents.append((ent, kb2_ent))
    print("num of matched ent pairs in kb1 and kb2:", len(matched_ents))

    ents1_set, ents2_set = pair_2set(matched_ents)
    source_related_ents_dict = generate_related_ents(source_triples)
    en_related_ents_dict = generate_related_ents(en_triples)
    ordered_dic = dict()
    for ent1, ent2 in matched_ents:
        degree1 = count_degree(ent1, ents1_set, source_related_ents_dict)
        degree2 = count_degree(ent2, ents2_set, en_related_ents_dict)
        ordered_dic[(ent1, ent2)] = degree1 + degree2
    ordered_pair = sorted(ordered_dic.items(), key=lambda d: d[1], reverse=True)
    ordered_matched_ents = [pair[0] for pair in ordered_pair]

    # Solve the one-to-many problem
    rel_ref_set = set()
    for rel in kb1_rels:
        ref = generate_matched_rel(rel, kb2_rels)
        if ref is not None and ref not in rel_ref_set:
            matched_rels.append((rel, ref))
            rel_ref_set.add(ref)
    print("num of ref rels in kb1 and kb2:", len(matched_rels))
    print_line()
    return ordered_matched_ents, matched_rels


def generate_matched_pairs(source_triples, en_triples, ill_pairs):
    print_line("start to generate matched pairs")
    links_dict = pair_2dict(ill_pairs)
    print("total num of ills between kb1 and kb2:", len(links_dict))
    kb1_ents, kb1_rels = parse_triples(source_triples)
    kb2_ents, kb2_rels = parse_triples(en_triples)
    print("num of triples, ents and rels in kb1:", len(source_triples), len(kb1_ents), len(kb1_rels))
    print("num of triples, ents and rels in kb2:", len(en_triples), len(kb2_ents), len(kb2_rels))
    matched_ents = list()
    matched_rels = list()
    for ent in kb1_ents:
        assert ent in links_dict
        kb2_ent = links_dict.get(ent)
        if kb2_ent in kb2_ents:
            matched_ents.append((ent, kb2_ent))
    print("num of matched ent pairs in kb1 and kb2:", len(matched_ents))

    # Solve the one-to-many problem
    rel_ref_set = set()
    for rel in kb1_rels:
        ref = generate_matched_rel(rel, kb2_rels)
        if ref is not None and ref not in rel_ref_set:
            matched_rels.append((rel, ref))
            rel_ref_set.add(ref)
    print("num of ref rels in kb1 and kb2:", len(matched_rels))
    print_line()
    return matched_ents, matched_rels


def generate_matched_closed_triples(triples, all_matched_ents, param):
    ents_set = set()
    for ent in all_matched_ents:
        ents_set.add(ent[param])
    return filter_triples_by_entset(triples, ents_set)


def read_all_triples(triples_file1, triples_file2):
    triples1 = read_triples(triples_file1)
    triples2 = read_triples(triples_file2)
    return triples1 | triples2


def triples_2id_2file(triples, ents_ids, rels_ids, file_path):
    """
    Write id triple to file
    :param triples:
    :param ents_ids:
    :param rels_ids:
    :param file_path:
    :return:
    """
    file = open(file_path, 'w', encoding='utf8')
    for triple in triples:
        assert triple[0] in ents_ids
        assert triple[1] in rels_ids
        assert triple[2] in ents_ids
        h = str(ents_ids.get(triple[0]))
        p = str(rels_ids.get(triple[1]))
        t = str(ents_ids.get(triple[2]))
        file.write(h + '\t' + p + '\t' + t + '\n')
    file.close()


def filter_triples_by_entset(ori_triples, ent_set):
    """
    Filter triplets, extract triplets with head and tail entities in a certain set of entities
    :param ori_triples:
    :param ent_set:
    :return:
    """
    triples = set()
    for triple in ori_triples:
        if triple[0] in ent_set and triple[2] in ent_set:
            triples.add(triple)
    return triples


def filter_triples_by_min(triples, min_sub):
    assert min_sub > 0
    ents_triples = dict()
    for triple in triples:
        ents_triples[triple[0]] = ents_triples.get(triple[0], 0) + 1
    ordered = sorted(ents_triples.items(), key=lambda d: d[1], reverse=True)
    ents = [order[0] for order in ordered if order[1] >= min_sub]
    ents = set(ents)
    print()
    print("ents of frequency > ", min_sub, ":", len(ents))
    print()
    return filter_triples_by_entset(triples, ents)


def generate_train_data_ordered(folder, kb1_triples_file, kb2_triples_file, matched_ents_file, matched_rels_file,
                                supervised_radio):
    kb1_triples = list(read_triples(kb1_triples_file))
    kb2_triples = list(read_triples(kb2_triples_file))
    matched_ents = read_pairs(matched_ents_file)
    matched_rels = read_pairs(matched_rels_file)
    print_line("start generate training data")
    print("num of triples in kb1:", len(kb1_triples))
    print("num of triples in kb2:", len(kb2_triples))
    kb1_ents, kb1_rels = parse_triples(kb1_triples)
    kb2_ents, kb2_rels = parse_triples(kb2_triples)
    print("num of ents and rels in kb1:", len(kb1_ents), len(kb1_rels))
    print("num of ents and rels in kb2:", len(kb2_ents), len(kb2_rels))
    print("num of ILLs:", len(matched_ents))
    sup_ents_pairs_num = int(len(matched_ents) * supervised_radio)
    sup_rels_pairs_num = int(len(matched_rels) * supervised_radio)
    sup_ents_pairs = random.sample(matched_ents, sup_ents_pairs_num)
    # sup_ents_pairs = matched_ents[0: sup_ents_pairs_num]
    # sup_ents_pairs = matched_ents[len(matched_ents) - sup_ents_pairs_num: len(matched_ents)]
    # This place to see how to deal with
    # sup_rels_pairs = random.sample(matched_rels, sup_rels_pairs_num)
    sup_rels_pairs = matched_rels
    print("num of sup ent pairs:", len(sup_ents_pairs))
    print("num of sup rel pairs:", len(sup_rels_pairs))

    kb1_ents_ids, kb2_ents_ids = generate_id(matched_ents, sup_ents_pairs, kb1_ents, kb2_ents,
                                             radio_2file(supervised_radio, folder) + 'ent_ids')
    kb1_rels_ids, kb2_rels_ids = generate_id(matched_rels, sup_rels_pairs, kb1_rels, kb2_rels,
                                             radio_2file(supervised_radio, folder) + 'rel_ids')

    pairs_ids_2file(sup_ents_pairs, kb1_ents_ids, kb2_ents_ids,
                    radio_2file(supervised_radio, folder) + 'sup_ent_ids')
    pairs_ids_2file(sup_rels_pairs, kb1_rels_ids, kb2_rels_ids,
                    radio_2file(supervised_radio, folder) + 'sup_rel_ids')

    latent_ref_ents_pairs = list(set(matched_ents) ^ set(sup_ents_pairs))
    latent_ref_rels_pairs = list(set(matched_rels) ^ set(sup_rels_pairs))
    latent_ref = list()
    for pair in latent_ref_ents_pairs:
        ent1_id = kb1_ents_ids.get(pair[0])
        ent2_id = kb2_ents_ids.get(pair[1])
        latent_ref.append((ent1_id, ent2_id))
    pairs_2file(latent_ref, radio_2file(supervised_radio, folder) + 'ref_ent_ids')
    pairs_2file(latent_ref_ents_pairs, radio_2file(supervised_radio, folder) + 'ref_ents')

    triples_2id_2file(kb1_triples, kb1_ents_ids, kb1_rels_ids, radio_2file(supervised_radio, folder) + 'triples_1')
    triples_2id_2file(kb2_triples, kb2_ents_ids, kb2_rels_ids, radio_2file(supervised_radio, folder) + 'triples_2')

    # 构造MTransE的id数据
    folder += "mtranse/"
    kb1_ents_ids, kb2_ents_ids = generate_id_MTranE(matched_ents, latent_ref_ents_pairs, sup_ents_pairs, kb1_ents,
                                                    kb2_ents, radio_2file(supervised_radio, folder) + 'ent_ids')
    kb1_rels_ids, kb2_rels_ids = generate_id_MTranE(matched_rels, latent_ref_rels_pairs, sup_rels_pairs, kb1_rels,
                                                    kb2_rels, radio_2file(supervised_radio, folder) + 'rel_ids')
    latent_ref = list()
    for pair in latent_ref_ents_pairs:
        ent1_id = kb1_ents_ids.get(pair[0])
        ent2_id = kb2_ents_ids.get(pair[1])
        latent_ref.append((ent1_id, ent2_id))
    pairs_2file(latent_ref, radio_2file(supervised_radio, folder) + 'ref_pairs')
    sup_ref = list()
    for pair in sup_ents_pairs:
        ent1_id = kb1_ents_ids.get(pair[0])
        ent2_id = kb2_ents_ids.get(pair[1])
        sup_ref.append((ent1_id, ent2_id))
    pairs_2file(sup_ref, radio_2file(supervised_radio, folder) + 'sup_pairs')

    triples_2id_2file(kb1_triples, kb1_ents_ids, kb1_rels_ids, radio_2file(supervised_radio, folder) + 'triples_1')
    triples_2id_2file(kb2_triples, kb2_ents_ids, kb2_rels_ids, radio_2file(supervised_radio, folder) + 'triples_2')


def generate_id(ref_pairs, sup_pairs, kb1_eles, kb2_eles, file_path):
    """
    To construct the data id, this step is the key, the construction method is:
     1) First construct the id of the element to be matched, the id of the element to be matched in the two knowledge bases has a difference, that is, the number of pairs to be matched
     2) Reconstruct the id of the supervised element pair, the supervised elements of the two knowledge bases have the same id
     3) Finally, the other id
    :param ref_pairs:
    :param sup_pairs:
    :param kb1_eles:
    :param kb2_eles:
    :param file_path:
    :return:
    """
    latent_ref_ents_id_diff = len(ref_pairs) - len(sup_pairs)
    print("id index diff:", latent_ref_ents_id_diff)
    latent_ref_pairs = list(set(ref_pairs) ^ set(sup_pairs))
    assert latent_ref_ents_id_diff == len(latent_ref_pairs)
    ids1, ids2 = dict(), dict()
    index = 0
    # Construct the id of the potential element to be matched
    for ref_pair in latent_ref_pairs:
        ids1[ref_pair[0]] = index
        ids2[ref_pair[1]] = index + latent_ref_ents_id_diff
        index += 1
    index += latent_ref_ents_id_diff
    # Construct supervised element id
    for ref_pair in sup_pairs:
        ids1[ref_pair[0]] = index
        ids2[ref_pair[1]] = index
        index += 1
    # Construct other id
    for ele in kb1_eles:
        if ele not in ids1:
            ids1[ele] = index
            index += 1
    for ele in kb2_eles:
        if ele not in ids2:
            ids2[ele] = index
            index += 1
    ids_2file(ids1, file_path + '_1')
    ids_2file(ids2, file_path + '_2')
    return ids1, ids2


def generate_id_MTranE(ref_pairs, latent_ref_pairs, sup_pairs, kb1_eles, kb2_eles, file_path):
    latent_ref_ents_id_diff = len(ref_pairs) - len(sup_pairs)
    print("id index diff:", latent_ref_ents_id_diff)
    assert latent_ref_ents_id_diff == len(latent_ref_pairs)
    ids1, ids2 = dict(), dict()
    index = 0
    # Construct the id of the potential element to be matched
    for ref_pair in latent_ref_pairs:
        ids1[ref_pair[0]] = index
        ids2[ref_pair[1]] = index + latent_ref_ents_id_diff
        index += 1
    index += latent_ref_ents_id_diff
    # Construct other id
    for ele in kb1_eles:
        if ele not in ids1:
            ids1[ele] = index
            index += 1
    for ele in kb2_eles:
        if ele not in ids2:
            ids2[ele] = index
            index += 1
    ids_2file(ids1, file_path + '_1')
    ids_2file(ids2, file_path + '_2')
    return ids1, ids2
