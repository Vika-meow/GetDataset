from rel_data_methods import *
from attr_data_methods import *
from conf import *
from data_utils import *


#(RU_FOLDER, RU_IB_FILE, RU_IBM_FILE, RU_DBO_FILE, RU_DBO_ATTR_FILE, RU_ENT_PREFIX)
#генерирует файлы all_rel_triplets all_attr_triplets
def generate_all_triples(folder, ib_file, ibm_file, dbo_obj_file, dbo_literal_file, ent_t_prefix):
    """
    Extract all rel triples and attr triples
    :param folder:The root directory of a language KB
    :param ib_file: infobox triples
    :param ibm_file: infobox mapped triples
    :param dbo_obj_file: relation triple file
    :param dbo_literal_file: attribute triple file
    :param ent_t_prefix:Tail entity prefix, constrained to DBpedia entity
    :return:
    """
    print_line("Start to generate triples ...")
    ib_file_lines = set(read_lines(ib_file))
    print_line("got ib_file")
    ibm_file_lines = set(read_lines(ibm_file))
    print_line("got ibm_file")
    dbo_obj_file_lines = set(read_lines(dbo_obj_file))
    print_line("got dbo_file")
    dbo_literal_file_lines = set(read_lines(dbo_literal_file))
    all_rel_lines = ib_file_lines | ibm_file_lines | dbo_obj_file_lines
    all_attr_lines = ib_file_lines | ibm_file_lines | dbo_literal_file_lines

    del ib_file_lines, ibm_file_lines, dbo_obj_file_lines, dbo_literal_file_lines
    print("all origin triples", len(all_rel_lines), len(all_attr_lines))
    # Construct all rel triples, write to file
    rel_lines = generate_all_rel_triples(folder, all_rel_lines, ent_t_prefix)
    attr_lines = all_attr_lines - rel_lines
    del rel_lines

    # Construct all attr data and write to file

    generate_all_attr_data(folder, attr_lines)


def generate_source_triples(rel_triples_file, ill_file, kb12_folder, rev=False,
                            ills_t_prefix='http://dbpedia.org/resource/'):
    rel_triples = read_triples(rel_triples_file)
    # important!!
    rel_triples = remove_dbo_triples(rel_triples)
    # Read the ill file, get ill matching pairs (default to English) and entity collection
    ill_pairs, ill_head_set, ill_tail_set = read_interlink(ill_file, ent_t_prefix=ills_t_prefix)
    ill_ents = ill_head_set if rev is False else ill_tail_set
    # Step 3, construct all closed triples, write to file
    all_closed_triples_set = generate_closed_triples(kb12_folder, rel_triples, ill_ents)
    # Step 4, construct a balanced and closed triplet (that is, each entity has both out and in degrees), write to the file
    generate_balance_closed_triples(kb12_folder, all_closed_triples_set)
    print("All done.")
    print_line()


#
def generate_kb12_triples(kb12_1folder, kb12_2folder, rel_triples_file1, rel_triples_file2, ill_file, ent1_prefix,
                          ent2_prefix):
    if not os.path.exists(kb12_1folder):
        os.makedirs(kb12_1folder)
    if not os.path.exists(kb12_2folder):
        os.makedirs(kb12_2folder)
    #generate_source_triples(rel_triples_file1, ill_file, kb12_1folder, ills_t_prefix=ent2_prefix)
    generate_source_triples(rel_triples_file2, ill_file, kb12_2folder, rev=True, ills_t_prefix=ent2_prefix)


def generate_train_data(out_folder, s_folder, t_folder, iil_file, t_ent_prefix, filter_th1, filter_th2,
                        supervised_radio=[0.5, 0.4, 0.3, 0.2, 0.1], ills_num=8000, target_ills_num=8000,
                        is_remove=False):
    print("Params: ", "filter1", filter_th1, "; filter2", filter_th2, "; is remove", is_remove)
    x_rel_triples = s_folder + ALL_REL_CLOSED_BALANCED_TRIPLES_FILE
    en_rel_triples = t_folder + ALL_REL_CLOSED_BALANCED_TRIPLES_FILE
    generate_source_en_train_triples(out_folder, x_rel_triples, iil_file, en_rel_triples, filter_th1, filter_th2,
                                     is_matched_close=True, min_sub=1, ills_num=ills_num,
                                     target_ills_num=target_ills_num, ills_t_prefix=t_ent_prefix, is_remove=is_remove)
    path = radio_2file(target_ills_num, out_folder)
    for radio in supervised_radio:
        generate_train_data_ordered(path, path + S_TRIPLES, path + T_TRIPLES, path + "ent_ILLs", path + "rel_ILLs",
                                    radio)


def generate_attrs_data(s_main_folder, t_main_folder, s_t_folder, is_sup_attrs=True):
    print_line("generate attrs...")
    s_all_attrs = s_main_folder + ALL_ATTRS_FILE
    t_all_attrs = t_main_folder + ALL_ATTRS_FILE
    generate_attrs_train_data(s_t_folder, s_all_attrs, t_all_attrs, is_sup_attrs)


def generate_attr_triples(s_main_folder, t_main_folder, out_folder, ills_num=15000):
    print_line("generate attrs...")
    s_all_attrs = s_main_folder + ALL_ATTR_TRIPLES_FILE
    t_all_attrs = t_main_folder + ALL_ATTR_TRIPLES_FILE
    ent_ills = read_pairs(out_folder + ENT_ILLS)
    ents1, ents2 = pair_2set(ent_ills)
    assert len(ent_ills) == len(ents1) == len(ents2) == ills_num
    generate_attr_triples_data(s_all_attrs, ents1, out_folder + S_ATTR_TRIPLES)
    generate_attr_triples_data(t_all_attrs, ents2, out_folder + T_ATTR_TRIPLES)


if __name__ == '__main__':

    # ru
    generate_all_triples(RU_FOLDER, RU_IB_FILE, RU_IBM_FILE, RU_DBO_FILE, RU_DBO_ATTR_FILE, RU_ENT_PREFIX)
    # en
    generate_all_triples(EN_FOLDER, EN_IB_FILE, EN_IBM_FILE, EN_DBO_FILE, EN_DBO_ATTR_FILE, EN_ENT_PREFIX)

    # ru-en-15k

    generate_kb12_triples(RU_EN_FOLDER + RU_FOLDER, RU_EN_FOLDER + EN_FOLDER, RU_FOLDER + ALL_REL_TRIPLES_FILE,
                          EN_FOLDER + ALL_REL_TRIPLES_FILE, RU_ILL_FILE, RU_ENT_PREFIX, EN_ENT_PREFIX)
    generate_train_data(RU_EN_FOLDER, RU_EN_FOLDER + RU_FOLDER, RU_EN_FOLDER + EN_FOLDER, RU_ILL_FILE, EN_ENT_PREFIX,
                        4, 1, ills_num=16000, target_ills_num=15000)
    generate_attrs_data(RU_FOLDER, EN_FOLDER, RU_EN_FOLDER + str(15000) + "/")
    # Generate all data set based on the above sub data
    generate_all_rel_data_set(RU_EN_FOLDER, RU_FOLDER, EN_FOLDER, ills_num=15000)
    generate_attr_triples(RU_FOLDER, EN_FOLDER, RU_EN_FOLDER + "15000/" + DATA_SET_FOLDER, ills_num=15000)
