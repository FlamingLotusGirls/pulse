#ifndef __LINKED_LIST_CSW_H__
#define __LINKED_LIST_CSW_H__

typedef struct __LinkedList{
    struct __LinkedList *next;
    void *data;
} LinkedList;


LinkedList* LinkedListAdd(   LinkedList *list, void *data);
LinkedList* LinkedListDelete(LinkedList *list, void *data);

#endif //__LINKED_LIST_CSW_H__